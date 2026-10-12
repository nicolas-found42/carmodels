"""Learn and generate editable cars. Public boundary: Generator prepare/train/generate/save/rebuild.

Numerical dependencies belong to the separate generator environment. Model judgments
are injected; this module never opens a provider client by itself.
"""
import json
from pathlib import Path
import re
import time

import numpy as np
import torch
import trimesh

from bake_models import bake_car
from generator_geometry import (ROOT, GRID, LIMITS, digest, json_bytes, write_json, aligned_parts,
                                body_grid, surface, fit_template, glb_bytes, validate_output,
                                read_parts)
from generator_judge import LABEL_THRESHOLD, NON_CAR_THRESHOLD

STAGES = ['interpret request', 'pick neighbour cars', 'sample shape', 'rebuild mesh',
          'place wheels', 'fit template', 'bake texture', 'validate', 'ready']
BODY_STYLES = ['coupe', 'sedan', 'hatchback', 'convertible', 'wagon', 'SUV', 'pickup', 'no match']
ERAS = [f'{year}s' for year in range(1930, 2030, 10)] + ['no match']


class ShapeVAE(torch.nn.Module):
    """Conditional 3D VAE over full 64-cubed grids; never trained during generation."""
    def __init__(self):
        super().__init__()
        self.encoder = torch.nn.Sequential(
            torch.nn.Conv3d(1, 4, 4, 2, 1), torch.nn.SiLU(),
            torch.nn.Conv3d(4, 8, 4, 2, 1), torch.nn.SiLU(),
            torch.nn.Conv3d(8, 16, 4, 2, 1), torch.nn.SiLU(), torch.nn.Flatten())
        self.mu = torch.nn.Linear(8192 + len(BODY_STYLES) + len(ERAS) + 3, 16)
        self.logvar = torch.nn.Linear(8192 + len(BODY_STYLES) + len(ERAS) + 3, 16)
        self.expand = torch.nn.Linear(16 + len(BODY_STYLES) + len(ERAS) + 3, 8192)
        self.decoder = torch.nn.Sequential(
            torch.nn.ConvTranspose3d(16, 8, 4, 2, 1), torch.nn.SiLU(),
            torch.nn.ConvTranspose3d(8, 4, 4, 2, 1), torch.nn.SiLU(),
            torch.nn.ConvTranspose3d(4, 1, 4, 2, 1))

    def encode(self, grid, condition):
        features = torch.cat([self.encoder(grid), condition], dim=1)
        return self.mu(features), self.logvar(features).clamp(-8, 4)

    def decode(self, latent, condition):
        features = self.expand(torch.cat([latent, condition], dim=1)).reshape(-1, 16, 8, 8, 8)
        return self.decoder(features)


def fit_wheel_model(features, targets):
    """Separate ridge regression for layout, learned from the body's embedding."""
    mean, spread = features.mean(0), np.maximum(features.std(0), 1e-6)
    normalized = np.column_stack([np.ones(len(features)), (features - mean) / spread])
    penalty = np.eye(normalized.shape[1]) * .5
    penalty[0, 0] = 0
    gram = np.einsum('ni,nj->ij', normalized, normalized)
    right = np.einsum('ni,nj->ij', normalized, targets)
    weights = np.linalg.solve(gram + penalty, right)
    if not np.isfinite(weights).all():
        raise ValueError('Non-finite learned wheel parameters')
    return {'mean': mean, 'spread': spread, 'weights': weights,
            'low': targets.min(0), 'high': targets.max(0)}


def learned_wheels(archive, prefix, features):
    normalized = np.r_[1., (features - archive[prefix + '_mean']) / archive[prefix + '_spread']]
    return np.clip(np.einsum('i,ij->j', normalized, archive[prefix + '_weights']),
                   archive[prefix + '_low'], archive[prefix + '_high'])


class Generator:
    def __init__(self, dealership=ROOT / 'dealership/dealership', assets=ROOT / 'dealership/generator', *, judge=None):
        self.dealership = Path(dealership).resolve()
        self.assets = Path(assets).resolve()
        self.cache = self.assets / 'cache'
        self.judge = judge
        self._corpus_grids = None

    def grid_for(self, entry):
        path = self.cache / f'{entry["code"]}.npy'
        if not path.is_file():
            body, _, _ = aligned_parts(self.dealership / 'models' / f'{entry["code"]}.glb', entry['game'])
            self.cache.mkdir(parents=True, exist_ok=True)
            np.save(path, body_grid(body), allow_pickle=False)
        grid = np.load(path, allow_pickle=False).astype(np.float32)
        if grid.shape != (GRID, GRID, GRID) or not np.isfinite(grid).all():
            raise ValueError('Invalid grid cache; rebuild with prepare')
        if entry.get('shape_sha256') and digest(grid.astype('<f2').tobytes()) != entry['shape_sha256']:
            raise ValueError('Grid cache differs from its canonical shape hash; rebuild with prepare')
        return grid

    def condition(self, entry, label):
        values = list(entry['proportions'])
        for field, options in [('bodyStyle', BODY_STYLES), ('era', ERAS)]:
            reading = label[field]
            accepted = reading['value'] if reading['probability'] >= LABEL_THRESHOLD else 'no match'
            values.extend(float(option == accepted) for option in options)
        return values

    def prepare(self, *, decisions=None):
        catalog = json.loads((self.dealership / 'catalog.json').read_text())
        entries, excluded, review, seen, shapes = [], [], [], set(), {}
        previous_labels = json.loads((self.assets / 'labels.json').read_text()) if (self.assets / 'labels.json').is_file() else {}
        self.cache.mkdir(parents=True, exist_ok=True)
        for entry in sorted(catalog, key=lambda e: e['code']):
            code = entry['code']
            if not re.fullmatch(r'[A-Z0-9_]+', code):
                raise ValueError('invalid dealership code')
            reason = None
            identity = re.sub(r'_(DAY|NIGHT)$', '', code) if code.startswith('GT_SIMULATION_') else code
            if code.startswith('GEN_'):
                reason = 'generated model'
            elif identity in seen:
                reason = 'duplicate shape'
            seen.add(identity)
            if reason:
                excluded.append({'code': code, 'reason': reason})
                continue
            path = self.dealership / 'models' / f'{code}.glb'
            game = entry.get('game', 'ford-racing-2')
            try:
                body, _, params = aligned_parts(path, game)
                previous = previous_labels.get(code, {})
                cached = self.cache / f'{code}.npy'
                grid = self.grid_for({'code': code, 'game': game}) if cached.is_file() and \
                    previous.get('glb_sha256') == digest(path.read_bytes()) else body_grid(body)
            except (ValueError, KeyError, OSError) as error:
                excluded.append({'code': code, 'reason': str(error)})
                continue
            row = {'code': code, 'name': entry.get('name', code), 'game': game,
                   'glb_sha256': digest(path.read_bytes()), 'grid_shape': [GRID] * 3, **params}
            # Canonical body occupancy is the learned shape. Paint, native codes,
            # archive copies and differing source triangulation do not multiply it.
            shape_hash = digest(grid.astype('<f2').tobytes())
            if shape_hash in shapes:
                excluded.append({'code': code, 'reason': 'duplicate shape',
                                 'duplicate_of': shapes[shape_hash], 'shape_sha256': shape_hash})
                continue
            shapes[shape_hash] = code
            row['shape_sha256'] = shape_hash
            entries.append(row)
            np.save(self.cache / f'{code}.npy', grid.astype(np.float16), allow_pickle=False)
            if len(entries) % 50 == 0:
                print(f'prepare grids: {len(entries)}', flush=True)
        if self.judge is None:
            raise ValueError('Preparation requires an injected judge or recorded judgment file')
        labels = self.judge.classify(entries)
        template_labels = self.judge.classify_template()
        kept = []
        for row in entries:
            label = labels[row['code']]
            probability = label['car_probability']
            if not isinstance(probability, (int, float)) or not np.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError('invalid car probability')
            decision = (decisions or {}).get(row['code'])
            if probability >= LABEL_THRESHOLD or decision == 'car':
                kept.append(row)
            elif probability <= NON_CAR_THRESHOLD or decision == 'not a car':
                excluded.append({'code': row['code'], 'reason': 'TypeSafe non-car probability',
                                 'car_probability': probability})
            else:
                review.append({**row, 'car_probability': probability})
        manifest = {'schema': 1, 'entries': kept, 'excluded': excluded, 'review': review, 'claim_limits': LIMITS}
        write_json(self.assets / 'labels.json', labels)
        write_json(self.assets / 'manifest.json', manifest)
        write_json(self.assets / 'review.json', review)
        write_json(self.assets / 'template-labels.json', template_labels)
        measurements = np.array([e['proportions'] + [e['boxiness']] for e in kept])
        if len(measurements):
            write_json(self.assets / 'calibration.json', {
                'schema': 1, 'manifest_sha256': digest(json_bytes(manifest)),
                'proportions': dict(zip(['length', 'height', 'width', 'boxiness'],
                                        np.quantile(measurements, [.1, .5, .9], axis=0).T.tolist())),
                'claim_limits': ['Shape-word levels map to corpus deciles/median, not human-validated semantic boundaries.']})
        return manifest

    def train(self, *, epochs=100, device=None):
        manifest_bytes = (self.assets / 'manifest.json').read_bytes()
        entries = json.loads(manifest_bytes)['entries']
        if len(entries) < 3:
            raise ValueError('Training requires at least three distinct cars')
        grids = np.stack([self.grid_for(e) for e in entries])
        heldout = list(range(0, len(entries), max(1, len(entries) // 10)))[:min(10, max(1, len(entries) // 10))]
        training = [i for i in range(len(entries)) if i not in heldout]
        neighbour_distances = [float(np.min(np.sqrt(np.mean((grids[training] - grids[i])**2, axis=(1, 2, 3)))))
                               for i in heldout]
        texture_threshold = float(np.quantile(neighbour_distances, .75))
        torch.manual_seed(35)
        torch.set_num_threads(4)
        flat = torch.from_numpy(grids[training].reshape(len(training), -1))
        mean = flat.mean(0)
        centred = flat - mean
        rank = min(16, len(training) - 1)
        _, singular, basis = torch.pca_lowrank(centred, q=rank, center=False, niter=4)
        np.savez_compressed(self.assets / 'basis.npz', mean=mean.numpy(), basis=basis.T.numpy(),
                            scale=(singular / np.sqrt(max(1, len(training) - 1))).numpy())
        labels = json.loads((self.assets / 'labels.json').read_text())
        conditions = torch.tensor([self.condition(e, labels[e['code']]) for e in entries], dtype=torch.float32)
        wheel_targets = np.array([[e['wheelbase'], e['track_width'], e['wheel_radius']] for e in entries])
        shape_features = (centred @ basis).numpy()
        wheel_models = {'shape': fit_wheel_model(shape_features, wheel_targets[training])}
        device = device or ('mps' if torch.backends.mps.is_available() else 'cpu')
        model = ShapeVAE().to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=.001)
        history, best, patience = [], float('inf'), 0
        order = np.random.default_rng(35)
        started = time.monotonic()
        for epoch in range(epochs):
            model.train()
            losses = []
            for batch in np.array_split(order.permutation(training), max(1, len(training) // 16)):
                inputs = torch.from_numpy(grids[batch, None]).to(device)
                cond = conditions[batch].to(device)
                mu, logvar = model.encode(inputs, cond)
                latent = mu + torch.randn_like(mu) * torch.exp(.5 * logvar)
                output = model.decode(latent, cond)
                # Emphasize the surface band; exterior distance dominates ordinary MSE.
                reconstruction = ((output - inputs).square() / (.03 + inputs.abs())).mean()
                kl = -.5 * (1 + logvar - mu.square() - logvar.exp()).mean()
                loss = reconstruction + .0001 * kl
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            model.eval()
            with torch.no_grad():
                target = torch.from_numpy(grids[heldout, None]).to(device)
                condition = conditions[heldout].to(device)
                mu, _ = model.encode(target, condition)
                error = float((model.decode(mu, condition) - target).square().mean().cpu())
            history.append({'epoch': epoch + 1, 'loss': float(np.mean(losses)), 'heldout_mse': error})
            if error < best:
                best, patience = error, 0
                torch.save({k: v.detach().cpu() for k, v in model.state_dict().items()}, self.assets / 'network.pt')
            else:
                patience += 1
            if epoch % 5 == 0:
                print(f'train {epoch + 1}/{epochs}: heldout MSE {error:.6f}', flush=True)
            if patience >= 12:
                break
        model.load_state_dict(torch.load(self.assets / 'network.pt', map_location=device, weights_only=True))
        with torch.no_grad():
            network_features = []
            for batch in np.array_split(np.array(training), max(1, len(training) // 16)):
                mu, _ = model.encode(torch.from_numpy(grids[batch, None]).to(device), conditions[batch].to(device))
                network_features.append(mu.cpu().numpy())
        wheel_models['network'] = fit_wheel_model(np.concatenate(network_features), wheel_targets[training])
        np.savez_compressed(self.assets / 'wheels.npz', **{prefix + '_' + key: value
                            for prefix, fitted in wheel_models.items() for key, value in fitted.items()})
        metadata = {'schema': 1, 'manifest_sha256': digest(manifest_bytes), 'codes': [e['code'] for e in entries],
                    'training': [entries[i]['code'] for i in training], 'heldout': [entries[i]['code'] for i in heldout],
                    'device': device, 'epochs': len(history), 'history': history,
                    'elapsed_seconds': time.monotonic() - started, 'novelty_default': .35,
                    'basis_sha256': digest((self.assets / 'basis.npz').read_bytes()),
                    'network_sha256': digest((self.assets / 'network.pt').read_bytes()),
                    'wheels_sha256': digest((self.assets / 'wheels.npz').read_bytes()),
                    'labels_sha256': digest((self.assets / 'labels.json').read_bytes()),
                    'calibration_sha256': digest((self.assets / 'calibration.json').read_bytes()),
                    'template_labels_sha256': digest((self.assets / 'template-labels.json').read_bytes()),
                    'texture_threshold': texture_threshold,
                    'texture_threshold_measurement': {'heldout_nearest_training_distances': neighbour_distances,
                                                       'quantile': .75},
                    'label_threshold': LABEL_THRESHOLD, 'claim_limits': LIMITS}
        write_json(self.assets / 'training.json', metadata)
        if self.assets == ROOT / 'dealership/generator' and self.dealership == ROOT / 'dealership/dealership':
            from generator_runtime import freshness
            freshness(write=True)
        return metadata

    def generate(self, *, method='shape space', seed=35, novelty=None, constraints=None, request='', artifact_pins=None,
                 emit=None, cancel=None, confirm=None):
        metadata = json.loads((self.assets / 'training.json').read_text())
        novelty = metadata['novelty_default'] if novelty is None else novelty
        if method not in ('shape space', 'network') or type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError('Invalid method or seed')
        if type(novelty) not in (int, float) or not np.isfinite(novelty) or not 0 <= novelty <= 1:
            raise ValueError('Novelty must be between zero and one')
        files = ['manifest.json', 'labels.json', 'template-labels.json', 'calibration.json', 'wheels.npz',
                 'basis.npz' if method == 'shape space' else 'network.pt']
        current_pins = {file: digest((self.assets / file).read_bytes()) for file in files}
        current_pins['appearance_policy'] = digest(b'solid paint and dark wheels; texture maps disabled v1')
        current_pins['training_settings'] = digest(json_bytes({key: metadata[key] for key in
                                                               ['training', 'label_threshold', 'texture_threshold']}))
        manifest = json.loads((self.assets / 'manifest.json').read_text())
        entries = manifest['entries']
        # Grids, donor geometry/materials and decoded palette all affect output.
        current_pins['source_glbs'] = digest(json_bytes({e['code']: digest(
            (self.dealership / 'models' / (e['code'] + '.glb')).read_bytes()) for e in entries}))
        catalog = json.loads((self.dealership / 'catalog.json').read_text())
        palette = [e['paint']['rgb'] for e in catalog if e.get('paint') and 'rgb' in e['paint']]
        current_pins['decoded_palette'] = digest(json_bytes(palette))
        if artifact_pins is not None and artifact_pins != current_pins:
            raise ValueError('Replay requires the recorded learned artifacts and labels')
        recipe = {'method': method, 'seed': seed, 'novelty': novelty,
                  'constraints': json.loads(json.dumps(constraints or {}, allow_nan=False)),
                  'artifact_pins': current_pins}
        current, started = None, time.monotonic()

        def event(stage, state, decisions):
            nonlocal current, started
            if cancel is not None and cancel.is_set():
                raise InterruptedError('Generation cancelled')
            if state == 'running':
                current, started = stage, time.monotonic()
            if emit:
                emit({'stage': stage, 'state': state, 'elapsed_seconds': time.monotonic() - started,
                      'decisions': decisions})
        try:
            event(STAGES[0], 'running', {})
            labels = json.loads((self.assets / 'labels.json').read_text())
            unsupported = []
            if request:
                if self.judge is None:
                    raise ValueError('Free text unavailable: use roll or dropdowns; TypeSafe is unavailable')
                interpretation = self.judge.interpret(request)
                interpreted = interpretation['constraints']
                for field in ('bodyStyle', 'era'):
                    if interpreted.get(field, {}).get('value') == 'no match' and field in recipe['constraints']:
                        interpreted[field] = {**recipe['constraints'][field], 'source': 'dropdown'}
                recipe['constraints'].update(interpreted)
                unsupported = interpretation.get('unsupported', [])
                calibration = json.loads((self.assets / 'calibration.json').read_text())['proportions']
                for target in recipe['constraints'].get('proportions', []):
                    target['value'] = float(np.interp(target['score'], [0, 1, 2], calibration[target['dimension']]))
            for field in ('bodyStyle', 'era'):
                reading = recipe['constraints'].get(field)
                if reading:
                    reading['applied'] = reading.get('applied', True) and reading['value'] != 'no match' and reading['probability'] >= metadata['label_threshold']
                if reading and reading['applied']:
                    supported = any(e['code'] in metadata['training'] and
                                    labels[e['code']][field]['probability'] >= metadata['label_threshold'] and
                                    labels[e['code']][field]['value'].lower() == reading['value'].lower() for e in entries)
                    if not supported:
                        unsupported.append(reading['value'] + ' (no confident training coverage)')
                        reading['applied'] = False
            if unsupported:
                event(STAGES[0], 'running', {'unsupported': unsupported, 'confirmation_required': True})
                if confirm is None or not confirm(unsupported):
                    raise InterruptedError('Unsupported request declined')
            event(STAGES[0], 'done', recipe['constraints'])
            event(STAGES[1], 'running', {})
            candidates = [e for e in entries if e['code'] in metadata['training']]
            for field in ('bodyStyle', 'era'):
                reading = recipe['constraints'].get(field)
                if reading and reading.get('applied', True) and reading.get('value') != 'no match' and reading.get('probability', 0) >= metadata['label_threshold']:
                    selected = [e for e in candidates if labels[e['code']][field]['probability'] >= metadata['label_threshold']
                                and labels[e['code']][field]['value'].lower() == reading['value'].lower()]
                    if not selected:
                        raise ValueError(f'No confident training labels match {reading["value"]}')
                    candidates = selected
            targets = [t for t in recipe['constraints'].get('proportions', [])
                       if t['probability'] >= metadata['label_threshold']]
            if targets:
                def proportion_distance(entry):
                    measurements = dict(zip(['length', 'height', 'width'], entry['proportions']))
                    measurements['boxiness'] = entry['boxiness']
                    return sum((measurements[t['dimension']] - t['value'])**2
                               for t in targets)
                candidates.sort(key=proportion_distance)
                candidates = candidates[:8]
            rng = np.random.default_rng(seed)
            anchor = candidates[int(rng.integers(len(candidates)))]
            anchor_grid = self.grid_for(anchor)
            corpus_key = (current_pins['manifest.json'], current_pins['source_glbs'])
            if self._corpus_grids is None or self._corpus_grids[0] != corpus_key:
                grids = np.stack([self.grid_for(e) for e in entries])
                grids.flags.writeable = False
                self._corpus_grids = (corpus_key, grids)
            all_grids = self._corpus_grids[1]
            distances = np.sqrt(np.mean((all_grids - anchor_grid)**2, axis=(1, 2, 3)))
            neighbours = np.argsort(distances)[:8]
            event(STAGES[1], 'done', {'neighbours': [{'code': entries[i]['code'], 'name': entries[i]['name'],
                                                    'distance': float(distances[i])} for i in neighbours]})
            event(STAGES[2], 'running', {})
            if method == 'shape space':
                basis = np.load(self.assets / 'basis.npz', allow_pickle=False)
                coefficients = np.einsum('ij,j->i', basis['basis'], anchor_grid.flatten() - basis['mean'])
                anchor_grid = (basis['mean'] + np.einsum('i,ij->j', coefficients, basis['basis'])).reshape([GRID] * 3)
                anchor_grid = (anchor_grid + anchor_grid[:, :, ::-1]) / 2
                direction = np.einsum('i,ij->j', rng.normal(size=len(basis['scale'])) * basis['scale'], basis['basis']).reshape([GRID] * 3)
            else:
                torch.set_num_threads(4)
                model = ShapeVAE()
                model.load_state_dict(torch.load(self.assets / 'network.pt', map_location='cpu', weights_only=True))
                model.eval()
                with torch.no_grad():
                    cond = torch.tensor([self.condition(anchor, labels[anchor['code']])], dtype=torch.float32)
                    mu, _ = model.encode(torch.from_numpy(anchor_grid[None, None]), cond)
                    base = model.decode(mu, cond)[0, 0].numpy()
                    latent = mu + torch.tensor(rng.normal(size=(1, 16)), dtype=torch.float32) * .5
                    direction = model.decode(latent, cond)[0, 0].numpy() - base
                    anchor_grid = (base + base[:, :, ::-1]) / 2
            direction = (direction + direction[:, :, ::-1]) / 2
            magnitude = float(np.sqrt(np.mean(direction**2)))
            distances = np.sqrt(np.mean((all_grids - anchor_grid)**2, axis=(1, 2, 3)))
            nearest = int(np.argmin(distances))
            if np.mean((anchor_grid - all_grids[nearest]) * direction) < 0:
                direction *= -1
            ordered = np.unique(np.sort(distances))
            limit = min(.045, max(.005, float(ordered[1] - ordered[0]) * .45)) if len(ordered) > 1 else .025
            grid = anchor_grid + novelty * limit / max(magnitude, 1e-8) * direction
            novelty_score = float(np.sqrt(np.mean((grid - anchor_grid)**2)))
            distances = np.sqrt(np.mean((all_grids - grid)**2, axis=(1, 2, 3)))
            nearest = int(np.argmin(distances))
            nearest_distance = float(distances[nearest])
            anchor = entries[nearest]
            event(STAGES[2], 'done', {'novelty_score': novelty_score, 'nearest_real_distance': nearest_distance,
                                    'method': method, 'seed': seed})
            event(STAGES[3], 'running', {})
            reconstructed = surface(grid)
            event(STAGES[3], 'done', {'surface_vertices': len(reconstructed.vertices)})
            event(STAGES[4], 'running', {})
            source_body, wheels, _ = aligned_parts(self.dealership / 'models' / f'{anchor["code"]}.glb', anchor['game'])
            layout = np.load(self.assets / 'wheels.npz', allow_pickle=False)
            if method == 'shape space':
                wheel_features = np.einsum('ij,j->i', basis['basis'], grid.flatten() - basis['mean'])
                wheelbase, track_width, wheel_radius = learned_wheels(layout, 'shape', wheel_features)
            else:
                with torch.no_grad():
                    wheel_features, _ = model.encode(torch.from_numpy(grid[None, None]), cond)
                wheelbase, track_width, wheel_radius = learned_wheels(layout, 'network', wheel_features[0].numpy())
            for wheel in wheels:
                vertices = np.concatenate([p['vertices'] for p in wheel])
                centre = (vertices.min(0) + vertices.max(0)) / 2
                desired = np.array([np.sign(centre[0]) * wheelbase / 2, wheel_radius,
                                    np.sign(centre[2]) * track_width / 2])
                scale = wheel_radius / (np.ptp(vertices[:, 1]) / 2)
                for part in wheel:
                    part['vertices'] = (part['vertices'] - centre) * scale + desired
            event(STAGES[4], 'done', {'wheel_source': anchor['name'], 'wheelbase': float(wheelbase),
                                    'track_width': float(track_width), 'wheel_radius': float(wheel_radius),
                                    'placement_model': 'learned ' + method})
            event(STAGES[5], 'running', {})
            body, uv, error = fit_template(grid, reconstructed)
            event(STAGES[5], 'done', {'template_fit_error': error, 'body_vertices': len(body.vertices)})
            event(STAGES[6], 'running', {})
            paint = palette[int(rng.integers(len(palette)))] if palette else [110, 132, 160]
            texture = None
            event(STAGES[6], 'done', {'texture': 'Texture maps disabled; solid body paint and dark wheels',
                                     'nearest_distance': nearest_distance})
            event(STAGES[7], 'running', {})
            data = glb_bytes(body, uv, texture, wheels, recipe, paint=paint)
            validation = validate_output(body, wheels, data)
            if not validation['passed']:
                raise ValueError('Generated symmetry or wheel contact failed validation')
            event(STAGES[7], 'done', validation)
            event(STAGES[8], 'running', {})
            code = 'GEN_' + digest(data)[:16].upper()
            result = {'code': code, 'glb': data, 'recipe': recipe, 'validation': validation,
                      'body_vertices': len(body.vertices), 'wheel_source': anchor['code'],
                      'novelty_score': novelty_score, 'nearest_real_distance': nearest_distance, 'request': request}
            event(STAGES[8], 'done', {'code': code, 'honesty_label': 'Generated model'})
            return result
        except Exception as error:
            if emit:
                emit({'stage': current, 'state': 'failed', 'elapsed_seconds': time.monotonic() - started,
                      'decisions': {'reason': str(error) if isinstance(error, (ValueError, InterruptedError)) else 'Generation failed'}})
            raise

    def save(self, result, *, name=None, output=None):
        import fcntl
        self.assets.mkdir(parents=True, exist_ok=True)
        with (self.dealership / '.generator-save.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self._save(result, name=name, output=output)

    def _save(self, result, *, name=None, output=None):
        from build_dealership import OUTPUT, build, compiled_text, load_all
        data = result['glb']
        code = 'GEN_' + digest(data)[:16].upper()
        if result.get('code') != code or not result['validation']['passed']:
            raise ValueError('Invalid generated model')
        bake_car(code, data, source_mode=False)
        catalog_path = self.dealership / 'catalog.json'
        original = catalog_path.read_bytes()
        catalog = json.loads(original)
        model = self.dealership / 'models' / f'{code}.glb'
        if any(e['code'] == code for e in catalog) or model.exists() or model.is_symlink():
            raise ValueError('Generated code already exists')
        constraints = result['recipe']['constraints']
        given = {k: v['value'] for k, v in constraints.items() if k in ('bodyStyle', 'era') and
                 v.get('applied', True) and v.get('probability', 0) >= LABEL_THRESHOLD and v.get('value') != 'no match'}
        default = 'Generated ' + ' · '.join([given.get('bodyStyle', 'car'), given.get('era', 'roll'), code[-6:].lower()])
        name = default if name is None or name == '' else name
        if not isinstance(name, str) or len(name) > 120 or any(ord(c) < 32 for c in name):
            raise ValueError('Name must contain up to 120 printable characters')
        entry = {'code': code, 'name': name, 'honestyLabel': 'Generated model', 'game': 'generated',
                 'gameLabel': 'Generated models', 'displayMode': 'textured-glb', 'group': 'GENERATED',
                 'sourceVariant': 'generated',
                 'bodyStyle': given.get('bodyStyle', 'unknown').lower(), 'era': given.get('era'),
                 'bodyStyleSource': 'requested' if 'bodyStyle' in given else None,
                 'eraSource': 'requested' if 'era' in given else None,
                 'year': None, 'bhp': None, 'kg': None, 'topSpeed': None, 'agility': None,
                 'speed': None, 'weight': None, 'accel': None, 'paint': None, 'sound': None,
                 'liveries': [], 'generator': {'recipe': result['recipe'], 'request': result.get('request', ''),
                                              'wheel_source': result['wheel_source']}, 'claimLimits': LIMITS}
        output = Path(output or OUTPUT)
        output.parent.mkdir(parents=True, exist_ok=True)
        previous_output = output.read_bytes() if output.is_file() else None
        created = False
        try:
            with model.open('xb') as stream:
                created = True
                stream.write(data)
            parts = read_parts(model, 'redline')
            body_parts = [p for p in parts if p['wheel'] is None]
            groups = sorted({p['wheel'] for p in parts if p['wheel'] is not None})
            wheels = [[p for p in parts if p['wheel'] == group] for group in groups]
            meshes = [trimesh.Trimesh(vertices=p['vertices'], faces=p['faces'], process=False) for p in body_parts]
            actual = validate_output(trimesh.util.concatenate(meshes), wheels, data)
            if not actual['passed']:
                raise ValueError('Generated symmetry or wheel contact failed save validation')
            separator = b',\n' if catalog else b'\n'
            appended = original.rstrip()[:-1].rstrip() + separator + json_bytes(entry).rstrip() + b'\n]\n'
            temporary_catalog = catalog_path.with_suffix('.generator.tmp')
            temporary_catalog.write_bytes(appended)
            temporary_catalog.replace(catalog_path)
            # Preflight all editable inputs before the builder changes display data.
            compiled_text(load_all(self.dealership))
            build(self.dealership, output)
        except Exception:
            if created:
                catalog_path.write_bytes(original)
                model.unlink(missing_ok=True)
                if previous_output is not None:
                    output.write_bytes(previous_output)
            raise
        return entry

    def rebuild(self, *, output=None):
        from build_dealership import OUTPUT, build
        return build(self.dealership, output or OUTPUT)


def main():
    import argparse
    import os
    from generator_judge import LiveJudge, RecordedJudge
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'train', 'generate', 'save', 'rebuild', 'worker'])
    parser.add_argument('--dealership', type=Path, default=ROOT / 'dealership/dealership')
    parser.add_argument('--assets', type=Path, default=ROOT / 'dealership/generator')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--device', choices=['cpu', 'mps'])
    parser.add_argument('--seed', type=int, default=35)
    parser.add_argument('--method', choices=['shape space', 'network'], default='shape space')
    parser.add_argument('--novelty', type=float)
    parser.add_argument('--request', default='')
    parser.add_argument('--constraints', type=Path)
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--name')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    # Reuse an existing local key without printing it or persisting it in artifacts.
    config = Path.home() / '.config/jgrep/env'
    if args.live and not os.environ.get('OPENROUTER_API_KEY') and config.is_file():
        for line in config.read_text().splitlines():
            if line.startswith('OPENROUTER_API_KEY='):
                os.environ['OPENROUTER_API_KEY'] = line.split('=', 1)[1].strip().strip('"\'')
    judge = LiveJudge(receipt=args.assets / 'judgments.json') if args.live else (
        RecordedJudge(args.assets / 'labels.json') if (args.assets / 'labels.json').is_file() else None)
    generator = Generator(args.dealership, args.assets, judge=judge)
    if args.command == 'worker':
        import sys
        from library_filter import model_status
        generator.judge = LiveJudge() if model_status() == 'available' else None
        options = json.loads((args.input / 'request.json').read_text())
        result = generator.generate(**options, emit=lambda e: print(json.dumps(e), flush=True),
                                    confirm=lambda parts: sys.stdin.readline().strip() == 'yes')
        (args.input / 'model.glb').write_bytes(result['glb'])
        write_json(args.input / 'model.json', {k: v for k, v in result.items() if k != 'glb'})
    elif args.command == 'prepare':
        decisions = json.loads(args.decisions.read_text()) if args.decisions else None
        result = generator.prepare(decisions=decisions)
        print(f'prepare: {len(result["entries"])} kept, {len(result["excluded"])} excluded, {len(result["review"])} await review')
    elif args.command == 'train':
        generator.train(epochs=args.epochs, device=args.device)
    elif args.command == 'generate':
        if args.output is None:
            parser.error('generate requires --output <new.glb>')
        constraints = json.loads(args.constraints.read_text()) if args.constraints else None
        result = generator.generate(method=args.method, seed=args.seed, novelty=args.novelty,
                                    constraints=constraints, request=args.request,
                                    emit=lambda e: print(json.dumps(e), flush=True),
                                    confirm=lambda parts: input(', '.join(parts) + ' unsupported. Continue without? [y/N] ') == 'y')
        with args.output.open('xb') as stream:
            stream.write(result['glb'])
        write_json(args.output.with_suffix('.json'), {k: v for k, v in result.items() if k != 'glb'})
    elif args.command == 'save':
        if args.input is None:
            parser.error('save requires --input <generated.glb>')
        result = json.loads(args.input.with_suffix('.json').read_text())
        result['glb'] = args.input.read_bytes()
        print(json.dumps(generator.save(result, name=args.name, output=args.output)))
    else:
        generator.rebuild(output=args.output)


if __name__ == '__main__':
    main()
