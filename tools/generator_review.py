"""Build 70 blind items, measure reconstruction, and summarize complete reviewer marks."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

ROOT = Path(__file__).resolve().parents[1]
LIMITS = ['Human marks measure recognition, not original-game fidelity or physical drivability.',
          'Ten held-out controls calibrate this reviewer; small samples are not population-wide estimates.']


def summarize(items, marks):
    if len(items) != 70 or len(marks) != 70 or set(marks) != {i['id'] for i in items} or \
            any(value not in ('car', 'not a car') for value in marks.values()):
        raise ValueError('All 70 blind items need car/not a car marks')
    methods = {}
    for method in ['shape space', 'network', 'control']:
        subset = [item for item in items if item['method'] == method]
        expected = 10 if method == 'control' else 30
        if len(subset) != expected:
            raise ValueError('Blind set requires 30 per method and 10 held-out controls')
        methods[method] = {'count': len(subset), 'car_rate': sum(marks[i['id']] == 'car' for i in subset) / len(subset)}
    groups = {}
    for novelty in sorted({i['novelty'] for i in items if i['method'] != 'control'}):
        groups[str(novelty)] = {}
        for method in ['shape space', 'network']:
            subset = [i for i in items if i['method'] == method and i['novelty'] == novelty]
            if subset:
                groups[str(novelty)][method] = sum(marks[i['id']] == 'car' for i in subset) / len(subset)
    acceptable = [float(n) for n, rates in groups.items() if len(rates) == 2 and
                  min(rates.values()) >= max(.8, methods['control']['car_rate'] - .1)]
    return {'schema': 1, 'methods': methods, 'novelty_groups': groups,
            'automatic_agreement': sum(i['automatic'] == (marks[i['id']] == 'car') for i in items) / 70,
            'novelty_default': max(acceptable) if acceptable else 0,
            'marks': marks, 'claim_limits': LIMITS}


def create(generator, folder):
    import numpy as np
    import torch
    from car_generator import ShapeVAE, json_bytes, write_json, learned_wheels
    folder = Path(folder)
    (folder / 'models').mkdir(parents=True, exist_ok=False)
    metadata = json.loads((generator.assets / 'training.json').read_text())
    manifest = json.loads((generator.assets / 'manifest.json').read_text())
    entries = {e['code']: e for e in manifest['entries']}
    labels = json.loads((generator.assets / 'labels.json').read_text())
    basis = np.load(generator.assets / 'basis.npz', allow_pickle=False)
    model = ShapeVAE()
    model.load_state_dict(torch.load(generator.assets / 'network.pt', map_location='cpu', weights_only=True))
    model.eval()
    wheel_models = np.load(generator.assets / 'wheels.npz', allow_pickle=False)
    quality = {'schema': 1, 'methods': {}, 'claim_limits': LIMITS}
    items = []
    for method in ['shape space', 'network']:
        errors, timing, distances, symmetry, contact, wheel_errors, fit_errors = [], [], [], [], [], [], []
        for code in metadata['heldout']:
            entry = entries[code]
            grid = generator.grid_for(entry)
            if method == 'shape space':
                delta = grid.flatten() - basis['mean']
                coefficients = np.einsum('ij,j->i', basis['basis'], delta)
                reconstructed = basis['mean'] + np.einsum('i,ij->j', coefficients, basis['basis'])
                placement = learned_wheels(wheel_models, 'shape', coefficients)
            else:
                with torch.no_grad():
                    condition = torch.tensor([generator.condition(entry, labels[code])], dtype=torch.float32)
                    mu, _ = model.encode(torch.from_numpy(grid[None, None]), condition)
                    reconstructed = model.decode(mu, condition)[0, 0].numpy().flatten()
                    placement = learned_wheels(wheel_models, 'network', mu[0].numpy())
            errors.append(float(np.mean((reconstructed - grid.flatten())**2)))
            wheel_errors.append((placement - [entry['wheelbase'], entry['track_width'], entry['wheel_radius']]).tolist())
        for i in range(30):
            novelty = [0, .35, .7][i // 10]
            started = time.monotonic()
            events = []
            result = generator.generate(method=method, seed=1000 + i % 10, novelty=novelty, emit=events.append)
            timing.append(time.monotonic() - started)
            distances.append(result['nearest_real_distance'])
            symmetry.append(result['validation']['symmetry_error'])
            contact.append(max(result['validation']['wheel_contact_errors']))
            fit_errors.append(next(e['decisions']['template_fit_error'] for e in events
                                   if e['stage'] == 'fit template' and e['state'] == 'done'))
            items.append({'method': method, 'novelty': novelty, 'seed': 1000 + i % 10,
                          'automatic': result['validation']['passed'], 'data': result['glb'],
                          'glb_sha256': hashlib.sha256(result['glb']).hexdigest()})
            print(f'review {method}: {i + 1}/30, {timing[-1]:.2f}s', flush=True)
        quality['methods'][method] = {'heldout_reconstruction_mse': errors, 'heldout_wheel_parameter_errors': wheel_errors,
            'template_fit_error': fit_errors, 'generation_seconds': timing,
            'nearest_real_distance': distances, 'symmetry_error': symmetry, 'wheel_contact_error': contact}
    for code in metadata['heldout'][:10]:
        data = (generator.dealership / 'models' / (code + '.glb')).read_bytes()
        items.append({'method': 'control', 'code': code, 'novelty': None, 'automatic': True,
                      'data': data, 'glb_sha256': hashlib.sha256(data).hexdigest()})
    if len(items) != 70:
        raise ValueError('Review requires ten real held-out controls')
    random.Random(35).shuffle(items)
    for i, item in enumerate(items):
        item['id'] = f'{i:02d}'
        (folder / 'models' / (item['id'] + '.glb')).write_bytes(item.pop('data'))
    session = hashlib.sha256(json_bytes(items)).hexdigest()
    write_json(folder / 'key.json', {'session': session, 'items': items})
    write_json(folder / 'presentation.json', {'session': session, 'items': [
        {'id': item['id'], 'model': f'./generator/review-session/models/{item["id"]}.glb',
         'sha256': item['glb_sha256']} for item in items]})
    write_json(generator.assets / 'quality.json', quality)
    return quality


def record(assets, payload):
    assets = Path(assets)
    key = json.loads((assets / 'review-session/key.json').read_text())
    if not isinstance(payload, dict) or set(payload) != {'session', 'marks'} or payload['session'] != key['session']:
        raise ValueError('Unknown review session')
    result = summarize(key['items'], payload['marks'])
    result['session'] = key['session']
    # Preserve the shuffled key and geometry hashes so future runs can audit the marks.
    result['items'] = key['items']
    classifications = assets / 'blind-classifications.json'
    if classifications.is_file():
        from generator_experiments import threshold_metrics
        readings = json.loads(classifications.read_text())
        if readings['session'] != key['session']:
            raise ValueError('TypeSafe classifications belong to a different blind session')
        rows = [{'code': item['id'], 'expected_car': payload['marks'][item['id']] == 'car'} for item in key['items']]
        result['typesafe_thresholds'] = threshold_metrics(rows, readings['labels'])
    def write_json(path, value):
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')
        temporary.replace(path)
    write_json(assets / 'review-results.json', result)
    metadata = json.loads((assets / 'training.json').read_text())
    metadata['novelty_default'] = result['novelty_default']
    metadata['novelty_review_sha256'] = hashlib.sha256((assets / 'review-results.json').read_bytes()).hexdigest()
    write_json(assets / 'training.json', metadata)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create', 'record'])
    parser.add_argument('--marks', type=Path)
    parser.add_argument('--assets', type=Path, default=ROOT / 'dealership/generator')
    args = parser.parse_args()
    if args.command == 'create':
        from car_generator import Generator
        create(Generator(assets=args.assets), args.assets / 'review-session')
    else:
        print(json.dumps(record(args.assets, json.loads(args.marks.read_text()))))
