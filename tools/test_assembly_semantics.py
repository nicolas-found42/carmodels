"""Corpus boundary/corruption controls for the source-named assembly decoder."""
import copy
import json
import math
import struct
import sys

from recover_assembly_semantics import ROOT, SOURCE, join, names, distance_root
sys.path.insert(0, str(SOURCE / 'tools'))
import ps2_sections

checks = []
def check(label, fn):
    fn()
    checks.append(label)
def reject(label, fn):
    try:
        fn()
    except (ValueError, UnicodeDecodeError):
        checks.append(label)
        return
    raise AssertionError(label)

thresholds = [0, 15, 45, 65, 380]
expected = [(0,0),(15,0),(math.nextafter(15,math.inf),1),(45,1),
            (math.nextafter(45,math.inf),2),(65,2),(math.nextafter(65,math.inf),3),
            (380,3),(math.nextafter(380,math.inf),4)]
for distance, root in expected:
    assert distance_root(distance, thresholds, 5) == root
    checks.append('threshold boundary ' + repr(distance))
assert distance_root(10, thresholds, 5, camera_scale=2) == 1
assert distance_root(10, thresholds, 5, minimum=2) == 2
assert distance_root(10, thresholds, 5, bias=9) == 3
assert distance_root(10, thresholds, 2, bias=-1, minimum=9) == 0
assert distance_root(400, thresholds, 5, minimum=9, bias=-1) == 4
assert distance_root(10, [], 5) == 4
checks.extend(['camera scale','minimum clamp','upper clamp','two-root lower clamp',
               'beyond final threshold bypasses bias/minimum','no thresholds uses last root'])
reject('nonfinite distance',lambda: distance_root(math.nan, thresholds, 5))
reject('invalid root count',lambda: distance_root(1, thresholds, 0))

data = next((ROOT / 'reference/ford/cars/GRAN_TORINO/model').iterdir()).read_bytes()
parsed = ps2_sections.parse(data)
base = join(data, parsed)
assert base['records'][0]['nodes'][6]['source_names'] or any(n['source_names'] for n in base['records'][0]['nodes'])
checks.append('original model parsed')
bad = bytearray(data); struct.pack_into('<I',bad,0,len(data)+1)
reject('name pool beyond file',lambda:names(bad))
bad = bytearray(data); struct.pack_into('<I',bad,8,0)
reject('name offset overlapping tables',lambda:names(bad))
bad = bytearray(data); struct.pack_into('<I',bad,4,len(data))
reject('oversized name count',lambda:names(bad))
span = next(s for s in parsed['later']['records'][0]['nodes_2c'] if s['pairs']['count'])
for word in (0,1):
    bad = bytearray(data); struct.pack_into('<I',bad,span['pairs']['offset']+word*4,65535)
    reject('out-of-range pair word '+str(word),lambda:join(bad,parsed))
bad = bytearray(data); struct.pack_into('<f',bad,span['offset']+8,math.nan)
reject('nonfinite translation',lambda:join(bad,parsed))
bad = bytearray(data); struct.pack_into('<I',bad,span['offset'],parsed['geometry']['table']['count'])
reject('invalid geometry index',lambda:join(bad,parsed))
mut = copy.deepcopy(parsed); mut['later']['records'][0]['nodes_2c'][0]['depth']=1
reject('missing parent',lambda:join(data,mut))
mut = copy.deepcopy(parsed); mut['later']['records'][0]['nodes_2c'][0]['children']+=1
reject('wrong direct child count',lambda:join(data,mut))
result = {'checks':len(checks),'failures':0,'cases':checks,
          'scope':'Decoder input checks and exact threshold/clamp controls; runtime values remain unobserved.'}
(ROOT/'research/evidence/continuation/assembly-controls.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
