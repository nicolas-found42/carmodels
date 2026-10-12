"""Measure bounded TypeSafe wording/threshold experiments, retaining raw receipts."""
import argparse
import hashlib
import json
from pathlib import Path

from generator_judge import LiveJudge

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = [.7, .8, .85, .9, .95]
LIMITS = ['Names and geometric summaries, not rendered visual judgment or retail identification.',
          'Small decoded/literal-name benchmark; selective accuracy excludes uncertain decisions.']


def threshold_metrics(rows, labels):
    metrics = []
    for threshold in THRESHOLDS:
        decisions = [(labels[r['code']]['car_probability'] >= threshold, r['expected_car']) for r in rows
                     if labels[r['code']]['car_probability'] >= threshold or
                     labels[r['code']]['car_probability'] <= 1 - threshold]
        metrics.append({'threshold': threshold, 'decided': len(decisions), 'count': len(rows),
                        'accuracy': sum(a == b for a, b in decisions) / len(decisions) if decisions else None})
    return metrics


def usage(calls):
    readings = [c['response'].get('usage', {}) for c in calls]
    return {'input_tokens': sum(r.get('input_tokens', 0) for r in readings),
            'output_tokens': sum(r.get('output_tokens', 0) for r in readings),
            'cost_usd': sum(r.get('cost', 0) for r in readings),
            'latency_seconds': sum(c['latency_seconds'] for c in calls)}


def measurements(path, game):
    import numpy as np
    import trimesh
    from generator_geometry import aligned_parts, read_parts
    try:
        _, _, params = aligned_parts(path, game)
        return params
    except ValueError:
        parts = read_parts(path, game)
        groups = sorted({p['wheel'] for p in parts if p['wheel'] is not None})
        wheels = [[p for p in parts if p['wheel'] == group] for group in groups]
        body = [p for p in parts if p['wheel'] is None]
        centres, radii, rays = [], [], []
        for wheel in wheels:
            vertices = np.concatenate([p['vertices'] for p in wheel])
            centre = (vertices.min(0) + vertices.max(0)) / 2
            centres.append(centre)
            radii.append(float(np.ptp(vertices[:, 1]) / 2))
            centre = centre.copy()
            centre[1] = vertices[:, 1].max() + .02
            rays.append(centre)
        if len(centres) < 2:
            raise ValueError('Benchmark needs measurable wheels')
        wheelbase = float(np.ptp(np.array(centres)[:, 0]))
        mesh = trimesh.util.concatenate([trimesh.Trimesh(vertices=p['vertices'], faces=p['faces'], process=False) for p in body])
        coverage = mesh.ray.intersects_any(np.array(rays), np.tile([0, 1, 0], (len(rays), 1)))
        scale = 2.5 / wheelbase
        return {'wheel_count': len(wheels), 'wheelbase': 2.5,
                'track_width': float(np.ptp(np.array(centres)[:, 2]) * scale),
                'wheel_radius': float(np.mean(radii) * scale), 'wheel_coverage': float(np.mean(coverage)),
                'proportions': (np.ptp(mesh.vertices, axis=0) * scale / [6, 3, 3]).tolist()}


def benchmark(assets, dealership):
    catalog = json.loads((dealership / 'catalog.json').read_text())
    old = json.loads((assets / 'experiments.json').read_text())
    codes = [r['code'] for r in old['rows']]
    codes += [e['code'] for e in catalog if 'BUGATTI_TYPE35GT' in e['code']]
    rows = []
    for code in codes:
        entry = next(e for e in catalog if e['code'] == code)
        path = dealership / 'models' / (code + '.glb')
        rows.append({'code': code, 'name': entry['name'], **measurements(path, entry.get('game', 'ford-racing-2')),
                     'glb_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'expected_car': entry.get('game', 'ford-racing-2') == 'ford-racing-2',
                     'decision_source': 'Decoded ordinary FR2 car, or literal bus/APC/drag/open-wheel class'})
    output = {'schema': 1, 'rows': rows, 'results': {}, 'claim_limits': LIMITS}
    for wording in ['brief', 'grounded']:
        judge = LiveJudge(receipt=assets / ('experiment-' + wording + '-judgments.json'), wording=wording)
        labels = judge.classify(rows)
        label_metrics = {}
        for field in ['bodyStyle', 'era']:
            known = [(r, next(e for e in catalog if e['code'] == r['code'])) for r in rows if r['expected_car']]
            values = []
            for threshold in THRESHOLDS:
                decisions = []
                for row, entry in known:
                    reading = labels[row['code']][field]
                    if reading['value'] == 'no match' or reading['probability'] < threshold:
                        continue
                    if field == 'bodyStyle':
                        expected = entry['bodyStyle']
                    else:
                        try:
                            expected = str(int(entry['year']) // 10 * 10) + 's'
                        except (ValueError, TypeError):
                            continue
                    # FR2's catalog predates generator vocabulary (e.g. racecar).
                    if field == 'bodyStyle' and expected not in ['coupe', 'sedan', 'hatchback', 'convertible', 'wagon', 'suv', 'pickup']:
                        continue
                    decisions.append(reading['value'].lower() == expected.lower())
                values.append({'threshold': threshold, 'decided': len(decisions),
                               'accuracy': sum(decisions) / len(decisions) if decisions else None})
            label_metrics[field] = values
        output['results'][wording] = {'labels': labels, 'thresholds': threshold_metrics(rows, labels),
                                      'label_metrics': label_metrics, **usage(judge.calls)}
    from generator_geometry import write_json
    write_json(assets / 'class-experiments.json', output)
    return output


def blind(assets, dealership):
    key = json.loads((assets / 'review-session/key.json').read_text())
    catalog = {e['code']: e for e in json.loads((dealership / 'catalog.json').read_text())}
    rows = []
    for item in key['items']:
        entry = catalog.get(item.get('code'), {})
        path = assets / 'review-session/models' / (item['id'] + '.glb')
        rows.append({'code': item['id'], 'name': entry.get('name', 'Unidentified vehicle'),
                     **measurements(path, entry.get('game', 'ford-racing-2') if entry else 'redline'),
                     'glb_sha256': item['glb_sha256']})
    judge = LiveJudge(receipt=assets / 'blind-judgments.json')
    labels = judge.classify(rows)
    from generator_geometry import write_json
    write_json(assets / 'blind-classifications.json', {'schema': 1, 'session': key['session'], 'labels': labels,
               **usage(judge.calls), 'claim_limits': LIMITS})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['benchmark', 'blind'])
    parser.add_argument('--assets', type=Path, default=ROOT / 'dealership/generator')
    parser.add_argument('--dealership', type=Path, default=ROOT / 'dealership/dealership')
    args = parser.parse_args()
    globals()[args.command](args.assets, args.dealership)
