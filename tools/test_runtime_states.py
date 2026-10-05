#!/usr/bin/env python3
"""Exercise capture binding and hierarchy corruption, including optimized Python."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'research/evidence/continuation/runtime'


def main():
    original = (BASE / 'race94-eeMemory.bin').read_bytes()
    joins = json.loads((BASE / 'race94-car-source-joins.json').read_text())
    observed = json.loads((BASE / 'race94-instance-states.json').read_text())
    car = observed['cars'][0]
    entity = car['entities'][0]
    states = entity['states']
    pair_node = next(s for s in states if (struct.unpack_from('<I', original, s['runtime_node'] + 4)[0] >> 8) & 63)
    pair_address = struct.unpack_from('<I', original, pair_node['runtime_node'] + 8)[0]
    mutable = next(s for s in states if s['mutable'])
    cases = [
        ('source_hash', None, 'EE capture hash differs from joins'),
        ('root_count', (car['descriptor'] + 0x11, b'\x00'), 'runtime root count differs'),
        ('class_registry', (car['descriptor'], struct.pack('<I', struct.unpack_from('<I', original, car['descriptor'])[0] ^ 1)), 'runtime class registry does not resolve descriptor'),
        ('geometry_id', (states[0]['runtime_node'], b'\xff\xff'), 'runtime geometry ID differs'),
        ('named_pair', (pair_address, b'\xff\xff'), 'runtime named pair differs'),
        ('descriptor_parent', (states[0]['runtime_node'] + 0x24, struct.pack('<I', 4)), 'runtime descriptor parent differs'),
        ('instance_parent', (states[1]['instance'], struct.pack('<I', 4)), 'runtime instance parent differs'),
        ('mutable_nonfinite', (mutable['instance'] + 0x10, struct.pack('<f', float('nan'))), 'nonfinite runtime mutable transform'),
        ('camera_nonfinite', (entity['address'] + 0x58, struct.pack('<f', float('inf'))), 'nonfinite camera-relative vector'),
        ('short_memory', 'truncate', 'EE memory must be exactly 32 MiB'),
    ]
    results = []
    with tempfile.TemporaryDirectory(dir=BASE, prefix='negative-controls-') as td:
        folder = Path(td)
        for name, mutation, expected in cases:
            data = bytearray(original)
            if mutation == 'truncate':
                data = data[:-1]
            elif mutation:
                offset, value = mutation
                data[offset:offset + len(value)] = value
            binding = dict(joins)
            binding['memory_sha256'] = hashlib.sha256(data).hexdigest()
            if name == 'source_hash':
                binding['memory_sha256'] = '0' * 64
            memory = folder / 'memory.bin'; memory.write_bytes(data)
            join_path = folder / 'joins.json'; join_path.write_text(json.dumps(binding))
            output = folder / 'unexpected-output.json'
            run = subprocess.run([sys.executable, '-O', str(ROOT / 'tools/trace_runtime_states.py'),
                                  '--memory', str(memory), '--joins', str(join_path), '--output', str(output)],
                                 capture_output=True, text=True)
            passed = run.returncode != 0 and expected in run.stderr and not output.exists()
            results.append({'control': name, 'passed': passed, 'expected_failure': expected,
                            'returncode': run.returncode, 'optimized_python': True})
            if not passed:
                raise RuntimeError(f'{name} did not fail closed: {run.stderr[-1000:]}')
    report = {'capture_sha256': hashlib.sha256(original).hexdigest(), 'controls': results,
              'failures': sum(not r['passed'] for r in results)}
    (BASE / 'runtime-state-negative-controls.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'controls': len(results), 'failures': report['failures']}))


if __name__ == '__main__':
    main()
