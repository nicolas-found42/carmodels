"""Stock-Python process boundary for cancellable generator jobs."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
STAGES = ['interpret request', 'pick neighbour cars', 'sample shape', 'rebuild mesh', 'place wheels',
          'fit template', 'bake texture', 'validate', 'ready']


def validate_start(payload):
    allowed = {'method', 'seed', 'novelty', 'constraints', 'request'}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise ValueError('Invalid generation request')
    if payload.get('method', 'shape space') not in ('shape space', 'network'):
        raise ValueError('Choose shape space or network')
    seed = payload.get('seed', 35)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Invalid seed')
    novelty = payload.get('novelty')
    if novelty is not None and (type(novelty) not in (int, float) or not 0 <= novelty <= 1):
        raise ValueError('Invalid novelty')
    request = payload.get('request', '')
    if not isinstance(request, str) or len(request) > 500 or any(ord(c) < 32 for c in request):
        raise ValueError('Enter at most 500 printable request characters')
    constraints = payload.get('constraints', {})
    if not isinstance(constraints, dict) or set(constraints) - {'bodyStyle', 'era'}:
        raise ValueError('Invalid dropdown constraints')
    for key, reading in constraints.items():
        styles = ['coupe', 'sedan', 'hatchback', 'convertible', 'wagon', 'SUV', 'pickup']
        eras = [f'{year}s' for year in range(1930, 2030, 10)]
        if not isinstance(reading, dict) or set(reading) != {'value', 'probability'} or \
                reading['probability'] != 1 or reading['value'] not in (styles if key == 'bodyStyle' else eras):
            raise ValueError('Invalid dropdown selection')
    return payload


def generator_python():
    return ROOT / '.venv-generator/bin/python'


def environment_available():
    if '--local-training' in __import__('sys').argv and os.environ.get('CI'):
        print('Fixture training is local only; CI runs inference against committed weights')
        return 1
    python = generator_python()
    if not python.is_file():
        print('Generator environment missing: provision .venv-generator using tools/generator-requirements.txt')
        return 1
    probe = "import importlib.metadata as m,sys; assert sys.version_info[:2]==(3,12); " + \
        "assert m.version('torch').split('+')[0]=='2.10.0'; " + \
        "assert all(m.version(k)==v for k,v in {'numpy':'2.2.6','scipy':'1.15.3','trimesh':'4.6.13','scikit-image':'0.25.2','pillow':'11.2.1','rtree':'1.4.0'}.items())"
    result = subprocess.run([str(python), '-c', probe], capture_output=True)
    if result.returncode:
        print('Generator environment does not match pinned Python 3.12 / numerical packages')
        return 2
    return 0


def freshness(root=ROOT, *, write=False):
    from verifier_common import finish, make_need, run_controls
    assets = Path(root) / 'dealership/generator'
    manifest = json.loads((assets / 'manifest.json').read_text())
    metadata = json.loads((assets / 'training.json').read_text())
    stale = []
    for entry in manifest['entries']:
        model = Path(root) / 'dealership/dealership/models' / (entry['code'] + '.glb')
        if not model.is_file() or hashlib.sha256(model.read_bytes()).hexdigest() != entry['glb_sha256']:
            stale.append(entry['code'])
    known = {e['code'] for field in ['entries', 'excluded', 'review'] for e in manifest[field]}
    catalog = json.loads((Path(root) / 'dealership/dealership/catalog.json').read_text())
    stale.extend(e['code'] for e in catalog if not e['code'].startswith('GEN_') and e['code'] not in known)
    pins = [('manifest.json', 'manifest_sha256'), ('labels.json', 'labels_sha256'),
            ('basis.npz', 'basis_sha256'), ('network.pt', 'network_sha256'), ('wheels.npz', 'wheels_sha256'),
            ('calibration.json', 'calibration_sha256'), ('template-labels.json', 'template_labels_sha256')]
    hashes = {file: hashlib.sha256((assets / file).read_bytes()).hexdigest() for file, _ in pins}
    need = make_need(ValueError)
    def derive(values):
        for file, pin in pins:
            need(values[file] == metadata[pin], 'Committed generator artifact differs from its training pin: ' + file)
        return values
    derive(hashes)
    controls = [(file, lambda values, key=file: values.update({key: '0' * 64})) for file, _ in pins]
    receipt = {'schema': 1, 'artifact_hashes': hashes, 'training_shapes': len(manifest['entries']),
               'controls': run_controls(hashes, controls, derive, ValueError),
               'claim_limits': ['Artifact/hash provenance and corruption controls only, not visual quality.',
                                'Changed dealership inputs warn about retraining; source staleness alone is not failure.']}
    path = Path(root) / 'research/evidence/car-generator/freshness.json'
    code = finish(receipt, path, ['--write'] if write else [], Path(root), {'check': 'generator freshness'})
    if code:
        raise ValueError('Generator freshness receipt differs')
    if stale:
        print('WARNING stale generator weights: ' + ', '.join(stale) +
              '; retrain with .venv-generator/bin/python tools/car_generator.py prepare --live then train')
    else:
        print('PASS generator freshness: all training GLBs and learned artifact hashes match')
    return stale


class GeneratorRuntime:
    def __init__(self, root=ROOT / 'dealership', *, python=None):
        self.root = Path(root).resolve()
        self.python = Path(python or generator_python())
        self.lock = threading.RLock()
        self.job = None

    def start(self, payload):
        validate_start(payload)
        with self.lock:
            if self.job and self.job['process'].poll() is None:
                raise BlockingIOError('A generation job is already running')
            if not self.python.is_file():
                raise RuntimeError('Generator environment unavailable; roll and dropdowns need the generator environment')
            if self.job:
                self.job['reader'].join(timeout=2)
                self.job['temporary'].cleanup()
            temporary = tempfile.TemporaryDirectory(prefix='carmodels-generator-')
            folder = Path(temporary.name).resolve()
            (folder / 'request.json').write_text(json.dumps(payload, allow_nan=False))
            log = (folder / 'worker.log').open('w')
            process = subprocess.Popen([str(self.python), str(ROOT / 'tools/car_generator.py'), 'worker',
                '--dealership', str(self.root / 'dealership'), '--assets', str(self.root / 'generator'),
                '--input', str(folder)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
            job = {'id': uuid.uuid4().hex, 'temporary': temporary, 'folder': folder, 'process': process,
                   'events': [{'stage': s, 'state': 'waiting', 'elapsed_seconds': 0, 'decisions': {}} for s in STAGES],
                   'status': 'running', 'stage_started': time.monotonic(), 'log': log}
            self.job = job
            job['reader'] = threading.Thread(target=self._read, args=(job,), daemon=True)
            job['reader'].start()
            return {'id': job['id'], 'status': job['status']}

    def close(self):
        if self.job:
            self.cancel(self.job['id'])

    def _read(self, job):
        for line in job['process'].stdout:
            try:
                event = json.loads(line)
                index = STAGES.index(event['stage'])
            except (ValueError, KeyError, TypeError):
                continue
            with self.lock:
                if job['status'] == 'cancelled':
                    continue
                job['events'][index] = event
                job['stage_started'] = time.monotonic()
                if event['state'] == 'failed':
                    job['status'] = 'failed'
                elif event['decisions'].get('confirmation_required'):
                    job['status'] = 'confirmation_required'
        status = job['process'].wait()
        job['process'].stdout.close()
        job['process'].stdin.close()
        job['log'].close()
        with self.lock:
            if job['status'] not in ('cancelled', 'failed'):
                job['status'] = 'ready' if status == 0 else 'failed'
                if status:
                    running = next((i for i, e in enumerate(job['events']) if e['state'] == 'running'), 0)
                    job['events'][running].update(state='failed', decisions={'reason': 'Generator worker failed'})

    def _job(self, job_id):
        if self.job is None or self.job['id'] != job_id:
            raise KeyError('Unknown generation job')
        return self.job

    def progress(self, job_id):
        with self.lock:
            job = self._job(job_id)
            events = json.loads(json.dumps(job['events']))
            for event in events:
                if event['state'] == 'running':
                    event['elapsed_seconds'] += time.monotonic() - job['stage_started']
            return {'id': job_id, 'status': job['status'], 'events': events,
                    'preview': f'/api/generator/{job_id}/model' if job['status'] == 'ready' else None}

    def latest(self):
        with self.lock:
            return self.progress(self.job['id']) if self.job else {'status': 'idle', 'events': [
                {'stage': s, 'state': 'waiting', 'elapsed_seconds': 0, 'decisions': {}} for s in STAGES]}

    def cancel(self, job_id):
        with self.lock:
            job = self._job(job_id)
            job['status'] = 'cancelled'
            process = job['process']
            if process.poll() is None:
                process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        job['reader'].join(timeout=2)
        job['temporary'].cleanup()
        return {'id': job_id, 'status': 'cancelled'}

    def confirm(self, job_id, accept):
        with self.lock:
            job = self._job(job_id)
            if job['status'] != 'confirmation_required':
                raise ValueError('Job is not awaiting confirmation')
            if accept:
                job['process'].stdin.write('yes\n')
                job['process'].stdin.flush()
                job['status'] = 'running'
                return {'id': job_id, 'status': 'running'}
        return self.cancel(job_id)

    def model(self, job_id):
        with self.lock:
            job = self._job(job_id)
            if job['status'] != 'ready':
                raise ValueError('Job is not ready')
            return (job['folder'] / 'model.glb').read_bytes()

    def save(self, job_id, name):
        with self.lock:
            job = self._job(job_id)
            if job['status'] != 'ready':
                raise ValueError('Job is not ready')
            process = subprocess.run([str(self.python), str(ROOT / 'tools/car_generator.py'), 'save',
                '--dealership', str(self.root / 'dealership'), '--assets', str(self.root / 'generator'),
                '--input', str(job['folder'] / 'model.glb'), '--name', name,
                '--output', str(self.root / 'public/dealership/cars.json')], capture_output=True, text=True)
            if process.returncode:
                raise ValueError('Save failed or generated code already exists')
            job['status'] = 'saved'
            return json.loads(process.stdout)


if __name__ == '__main__':
    import sys
    if '--freshness' in sys.argv:
        freshness(write='--write' in sys.argv)
    else:
        sys.exit(environment_available())
