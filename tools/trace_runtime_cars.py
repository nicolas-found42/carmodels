#!/usr/bin/env python3
"""Join paused EE source positions and relocated name arrays to original car objects."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def occurrences(haystack, needle):
    start = 0
    while True:
        start = haystack.find(needle, start)
        if start < 0:
            return
        yield start
        start += 1


def u32(data, offset):
    if offset < 0 or offset + 4 > len(data):
        raise ValueError('memory word outside capture')
    return struct.unpack_from('<I', data, offset)[0]


def source_tables(source):
    cursor = 4
    tables = []
    for _ in range(10):
        count = u32(source, cursor)
        cursor += 4
        tables.append((cursor, count, [u32(source, cursor+i*4) for i in range(count)]))
        cursor += count * 4
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--memory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    memory = args.memory.read_bytes()
    assert len(memory) == 32 * 1024 * 1024
    census = json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text())
    table_fields = [0x88,0x8c,0x9c,0x90,0x94,0x98,0xa0,0xa4,0xa8,0xac]
    count_fields = [0xb4,0xb8,0xc8,0xbc,0xc0,0xc4,0xcc,0xd0,0xd4,0xd8]
    cars = []
    for car in census['cars']:
        source = next((ROOT/'reference/ford/cars'/car['code']/'model').iterdir()).read_bytes()
        assert hashlib.sha256(source).hexdigest() == car['sha256']
        tables = source_tables(source)
        anchors = sorted((h['planes']['six_byte'] for h in car['geometry']['headers']),
                         key=lambda h: h['size'], reverse=True)[:3]
        bases = None
        anchors_report = []
        for span in anchors:
            payload = source[span['offset']:span['end']]
            hits = list(occurrences(memory, payload))
            possible = {h-span['offset'] for h in hits if h >= span['offset']}
            bases = possible if bases is None else bases & possible
            anchors_report.append({'source_offset': span['offset'], 'bytes':len(payload),
                                   'sha256':hashlib.sha256(payload).hexdigest(),'ee_hits':hits})
        joined = []
        for base in sorted(bases or set()):
            if base + len(source) > len(memory):
                continue
            # FUN_00123908 relocates each source name offset in place.
            if not all(u32(memory,base+offset+i*4)==base+value
                       for offset,count,values in tables for i,value in enumerate(values)):
                continue
            objects = []
            for hit in occurrences(memory, struct.pack('<I',base)):
                obj = hit - 0x84
                if obj < 0 or obj + 0xf0 > len(memory) or obj % 4:
                    continue
                if all(u32(memory,obj+field)==base+table[0] and u32(memory,obj+count_field)==table[1]
                       for field,count_field,table in zip(table_fields,count_fields,tables)):
                    objects.append({'address':obj,'texture_pointer_table':u32(memory,obj+0xec),
                                    'name_base':base,'all_ten_name_table_fields_match':True})
            joined.append({'source_base':base,'objects':objects,'relocated_name_offsets_match':True})
        if joined:
            cars.append({'car':car['code'],'source_sha256':car['sha256'],
                         'anchors':anchors_report,'joins':joined})
    report = {'memory':str(args.memory.resolve()),'memory_sha256':hashlib.sha256(memory).hexdigest(),
              'cars_with_source_join':len(cars),'cars':cars,
              'contract':'Three complete source position planes and all relocated name offsets; car object identified by all ten source table pointers and counts from FUN_00123908.',
              'limits':'Loaded objects and retained source buffers do not prove selected draws, visibility or geometry equivalence.'}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
