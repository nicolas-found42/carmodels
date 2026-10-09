#!/usr/bin/env python3
"""Measure original strip orientation and terminal distance roots; never infer shading."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from recover_assembly_semantics import distance_root

ROOT = Path(__file__).resolve().parents[1]


def audit():
    census_path = ROOT/'research/evidence/original-recovery/car-asset-census.json'
    assembly_path = ROOT/'research/evidence/continuation/assembly-semantics.json'
    census = json.loads(census_path.read_text())
    assembly = {c['code']: c for c in json.loads(assembly_path.read_text())['cars']}
    results = []
    for car in census['cars']:
        path = next((ROOT/'ford-racing-2/cars'/car['code']/'model').iterdir())
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != car['sha256']:
            raise ValueError('original source identity differs')
        record_counts = []
        cursor = 0
        for record, groups in enumerate(car['geometry']['group_header_counts']):
            bbox = struct.unpack_from('<6f', data, car['geometry']['table']['offset']+record*52+4)
            scales = [max(abs(bbox[2*i]), abs(bbox[2*i+1]))/16384 for i in range(3)]
            counts = Counter()
            headers = car['geometry']['headers'][cursor:cursor+sum(groups)]
            cursor += sum(groups)
            for h in headers:
                p = h['planes']['six_byte']
                raw = list(struct.iter_unpack('<3h', data[p['offset']:p['end']]))
                p = h['planes']['four_byte']
                packed = list(struct.iter_unpack('<4b', data[p['offset']:p['end']]))
                if len(raw) != h['count'] or len(packed) != h['count']:
                    raise ValueError('attribute bounds differ')
                positions = [[v[j]*scales[j] for j in range(3)] for v in raw]
                for i in range(2, len(raw)):
                    if packed[i][3] != 0:
                        counts['source_suppressed'] += 1
                        continue
                    a,b,c = (i-2,i-1,i) if i%2 == 0 else (i-1,i-2,i)
                    if len({raw[a],raw[b],raw[c]}) < 3:
                        counts['repeated_position'] += 1
                        continue
                    u = [positions[b][j]-positions[a][j] for j in range(3)]
                    v = [positions[c][j]-positions[a][j] for j in range(3)]
                    cross = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    mean = [sum(packed[k][j] for k in (a,b,c)) for j in range(3)]
                    dot = sum(cross[j]*mean[j] for j in range(3))
                    norm = math.sqrt(sum(x*x for x in cross)*sum(x*x for x in mean))
                    if not norm:
                        counts['zero_cross_or_normal'] += 1
                    elif abs(dot/norm) < 1e-6:
                        counts['perpendicular'] += 1
                    else:
                        counts['positive_dot' if dot > 0 else 'negative_dot'] += 1
            record_counts.append({'record':record,'counts':dict(counts)})
        roots = []
        for entry in assembly[car['code']]['records']:
            root = entry['roots'][-1]
            node = entry['nodes'][root]
            geometry = node['geometry_record']
            threshold = entry['thresholds'][-1]
            next_float = struct.unpack('<f',struct.pack('<I',struct.unpack('<I',struct.pack('<f',threshold))[0]+1))[0]
            roots.append({'assembly':entry['record'],'thresholds':entry['thresholds'],
                          'terminal_root_offset':node['offset'],'geometry_record':geometry,
                          'geometry_group_counts':car['geometry']['group_header_counts'][geometry],
                          'children':len(node['children']),
                          'at_final_threshold':distance_root(threshold,entry['thresholds'],len(entry['roots'])),
                          'one_float32_above':distance_root(next_float,entry['thresholds'],len(entry['roots'])),
                          'selector_bias':0,'selector_minimum':0,
                          'terminal_empty':not node['children'] and sum(car['geometry']['group_header_counts'][geometry])==0})
        total = Counter()
        for r in record_counts:total.update(r['counts'])
        results.append({'car':car['code'],'source_sha256':car['sha256'],
                        'orientation_counts':dict(total),'records':record_counts,'distance_roots':roots})
    output = {'census_sha256':hashlib.sha256(census_path.read_bytes()).hexdigest(),
              'assembly_sha256':hashlib.sha256(assembly_path.read_bytes()).hexdigest(),
              'cars':results,'limits':['Dot signs compare source strip winding with packed XYZ values; they do not prove those values are final normals.',
                                      'Terminal root checks use zero bias/minimum and scalar source helper; scene visibility and draw execution are separate.']}
    path = ROOT/'research/evidence/continuation/source-geometry-audit.json'
    path.write_text(json.dumps(output,indent=2)+'\n')
    total = Counter()
    for r in results:total.update(r['orientation_counts'])
    print(json.dumps({'cars':len(results),'orientation_counts':dict(total),
                      'terminal_empty':sum(x['terminal_empty'] for r in results for x in r['distance_roots']),
                      'assemblies':sum(len(r['distance_roots']) for r in results)}))


if __name__ == '__main__':audit()
