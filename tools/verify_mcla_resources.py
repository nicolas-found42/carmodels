#!/usr/bin/env python3
"""Verify that every RSC5 resource on the Midnight Club: Los Angeles disc decompresses exactly.

Opens the pinned disc, decrypts each RPF3 table (key located in the disc's own executable), and
decompresses every resource with the repo-owned LZX reader (`tools/mcla_lzx.py`). Each output must
equal the virtual plus physical size its archive flag word declares. The receipt records counts,
sizes and a digest of every output per archive; nested RPF3 archives inside the cache are opened
too. Controls corrupt a real resource and require each corruption to be rejected for its own reason.

Run from the repository root; `--write` establishes the receipt, a normal run must reproduce it.
`--available` exits 0 only when the pinned disc is present.
"""
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

import extract_mcla_cars
from mcla_lzx import WINDOW_BITS, LzxError, decompress, parse_header
from mcla_rpf import Rpf3Archive
import verifier_common
from xdvdfs import XdvdfsDisc

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'research/evidence/midnight-club-los-angeles/resources.json'
INDEX = ROOT / 'midnight-club-los-angeles/cars/index.json'
LIMITS = [
    'Establishes byte-exact decompression of every RSC5 resource to its declared size and records output '
    'digests; it does not decode the structures inside the outputs (see the model, texture and tuning checks).',
    'The chunk framing and the constant header word are readings checked on this disc only.',
    'The Intel E8 translation of LZX is not implemented; no resource on this disc sets it (the reader rejects it).',
]


class VerifyError(ValueError):
    pass


need = verifier_common.make_need(VerifyError)


def resource_tasks(iso):
    """(archive, entry index, ISO offset, stored size, flag, type) for every resource, plus nested archive facts."""
    disc = XdvdfsDisc(iso)
    try:
        image, archives, _key_record = extract_mcla_cars.open_archives(disc)
        key = extract_mcla_cars.locate_key(image)[0]
        by_path = {e['path']: e for e in disc.entries}
        tasks, nested = [], []
        for path in sorted(archives):
            archive, base = archives[path], disc.offset(by_path[path]['sector'])
            for entry in archive.entries:
                if entry['kind'] != 'file':
                    continue
                if entry['resource']:
                    tasks.append((path, entry['index'], base + entry['offset'], entry['stored'], entry['flag'],
                                  entry['resource_type']))
                    continue
                data = archive.payload(entry)
                if data[:4] == b'RPF3':
                    inner = Rpf3Archive(lambda at, size, data=data: data[at:at + size], len(data), key)
                    count = sum(1 for e in inner.entries if e['kind'] == 'file' and e['resource'])
                    nested.append({'archive': path, 'entry': entry['index'], 'entries': inner.count, 'resources': count})
        return tasks, nested
    finally:
        disc.close()


def decode_one(task, iso):
    path, index, offset, stored, flag, kind = task
    with open(iso, 'rb') as stream:
        stream.seek(offset)
        data = stream.read(stored)
    try:
        out, header = decompress(data)
    except LzxError as error:
        return {'archive': path, 'entry': index, 'error': str(error)}
    return {'archive': path, 'entry': index, 'type': kind, 'flag_matches': header['flag'] == flag,
            'type_matches': header['type'] & 0xFF == kind, 'constant': header['constant'],
            'chunks': header['chunks'], 'stored': stored, 'bytes': len(out),
            'sha256': hashlib.sha256(out).hexdigest()}


def _decode_star(args):
    return decode_one(*args)


def decode_all(tasks, iso, processes):
    jobs = [(task, str(iso)) for task in sorted(tasks, key=lambda t: -t[3])]
    if processes <= 1:
        return [decode_one(*job) for job in jobs]
    with ProcessPoolExecutor(processes) as pool:
        return list(pool.map(_decode_star, jobs, chunksize=8))


def summarise(results, nested):
    failures = [r for r in results if 'error' in r]
    need(not failures, 'resource failed to decompress: %s entry %d: %s' % (
        failures[0]['archive'], failures[0]['entry'], failures[0]['error']) if failures else '')
    need(all(r['flag_matches'] for r in results), 'RSC5 flag differs from the archive flag word')
    need(all(r['type_matches'] for r in results), 'RSC5 type differs from the archive resource type')
    constants = sorted({r['constant'] for r in results})
    need(constants == [0x0FF512EF], 'unexpected RSC5 header constant')
    archives, types = {}, {}
    for path in sorted({r['archive'] for r in results}):
        rows = sorted((r for r in results if r['archive'] == path), key=lambda r: r['entry'])
        lines = ''.join('%d %s\n' % (r['entry'], r['sha256']) for r in rows).encode()
        archives[path] = {'resources': len(rows), 'stored_bytes': sum(r['stored'] for r in rows),
                          'output_bytes': sum(r['bytes'] for r in rows), 'chunks': sum(r['chunks'] for r in rows),
                          'outputs_sha256': hashlib.sha256(lines).hexdigest()}
    for row in results:
        slot = types.setdefault(str(row['type']), {'resources': 0, 'output_bytes': 0})
        slot['resources'] += 1
        slot['output_bytes'] += row['bytes']
    return {'archives': archives, 'by_type': dict(sorted(types.items(), key=lambda kv: int(kv[0]))),
            'nested_archives': nested, 'header_constant': '0x%08x' % constants[0],
            'totals': {'resources': len(results), 'output_bytes': sum(r['bytes'] for r in results),
                       'chunks': sum(r['chunks'] for r in results)}}


def control_sample(tasks, iso):
    """The smallest streaming pack map (type 19) of the cache, read as stored."""
    task = min((t for t in tasks if t[5] == 19), key=lambda t: (t[3], t[1]))
    with open(iso, 'rb') as stream:
        stream.seek(task[2])
        return task, stream.read(task[3])


def with_body(data, body):
    return data[:16] + struct.pack('>I', len(body)) + body


def run_controls(data, digest):
    """Each corruption of a real resource must fail for the reason named beside it."""
    body = data[20:]
    flipped_type = bytearray(data)
    flipped_type[20 + (5 if body[0] == 0xFF else 2) + 1] ^= 0x40  # stream bit 1: verbatim 001 becomes 101
    flipped_body = bytearray(data)
    flipped_body[len(data) - 64] ^= 0x01
    last = body[5:] if body[0] == 0xFF else body[2:]
    need(len(last) + (5 if body[0] == 0xFF else 2) == len(body), 'control sample must be a single chunk')
    truncated = body[:1] + struct.pack('>HH', struct.unpack_from('>H', body, 1)[0], len(last) - 4) + last[:-4]
    controls = [
        ('truncated stream (last 4 bytes of the chunk removed, lengths adjusted)', with_body(data, truncated), {},
         'truncated'),
        ('flipped block-type bit', bytes(flipped_type), {}, 'block type'),
        ('declared size 4096 bytes short', data, {'expected': None, 'delta': -4096}, 'exceeds declared size'),
        ('declared size 4096 bytes long', data, {'expected': None, 'delta': 4096}, 'bytes, declared'),
        ('window 2**16 instead of 2**17', data, {'window_bits': 16}, 'tree'),
        ('window 2**18 instead of 2**17', data, {'window_bits': 18}, 'tree'),
        ('flipped bit near the end of the body', bytes(flipped_body), {}, None),
    ]
    results = []
    for label, sample, options, reason in controls:
        kwargs = {k: v for k, v in options.items() if k == 'window_bits'}
        if 'delta' in options:
            header = parse_header(sample)
            kwargs['expected'] = header['virtual'] + header['physical'] + options['delta']
        try:
            out, _ = decompress(sample, **kwargs)
        except LzxError as error:
            need(reason is None or reason in str(error), 'control %r failed for another reason: %s' % (label, error))
            results.append({'mutation': label, 'rejected': True, 'by': 'decoder error', 'reason': str(error)})
            continue
        need(reason is None, 'control escaped: ' + label)
        need(hashlib.sha256(out).hexdigest() != digest, 'control escaped: ' + label)
        results.append({'mutation': label, 'rejected': True, 'by': 'output digest differs',
                        'reason': 'the output differs from the recorded digest'})
    return results


def derive(iso, processes):
    index = json.loads(INDEX.read_text())
    pin = index['source']['sha256']
    need(extract_mcla_cars.source_digests(iso)[0] == pin, 'disc image differs from the pinned SHA-256')
    tasks, nested = resource_tasks(iso)
    results = decode_all(tasks, iso, processes)
    summary = summarise(results, nested)
    task, sample = control_sample(tasks, iso)
    clean = next(r for r in results if (r['archive'], r['entry']) == (task[0], task[1]))
    summary['controls'] = {'sample': {'archive': task[0], 'entry': task[1], 'stored_bytes': task[3],
                                      'output_sha256': clean['sha256']},
                           'results': run_controls(sample, clean['sha256'])}
    return {'schema': 1, 'tool': 'tools/verify_mcla_resources.py', 'decoder': 'tools/mcla_lzx.py',
            'window_bits': WINDOW_BITS, 'source': {'file': index['source']['file'], 'sha256': pin}, **summary,
            'claim_limits': LIMITS}


def main(argv):
    iso = Path(next((a.split('=', 1)[1] for a in argv if a.startswith('--iso=')), extract_mcla_cars.DEFAULT_ISO))
    if '--available' in argv:
        return 0 if iso.is_file() else 1
    if not iso.is_file():
        print('MISSING INPUT: the pinned MCLA disc image (%s)' % iso.name)
        return 1
    processes = int(next((a.split('=', 1)[1] for a in argv if a.startswith('--processes=')), os.cpu_count() or 1))
    try:
        receipt = derive(iso, processes)
    except (VerifyError, LzxError, ValueError) as error:
        print('VERIFY FAILED:', error)
        return 1
    totals = receipt['totals']
    summary = {'resources': totals['resources'], 'output_bytes': totals['output_bytes'],
               'controls_rejected': len(receipt['controls']['results'])}
    return verifier_common.finish(receipt, RECEIPT, argv, ROOT, summary)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
