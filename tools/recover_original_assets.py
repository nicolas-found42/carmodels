#!/usr/bin/env python3
"""Export bounded original level-zero textures and inspect every car container.

Uses the existing loader-derived reverse-engineering parsers without modifying
them. Raw alpha is preserved; display PNGs explicitly map alpha a to min(255,2*a).
Geometry spans are evidence, not a completed original mesh export.
"""
import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parents[1] / 'reverse-engineering'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def png_bytes(width, height, rgba):
    if len(rgba) != width * height * 4:
        raise ValueError('RGBA length differs from dimensions')
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))
    scan = b''.join(b'\0' + rgba[y*width*4:(y+1)*width*4] for y in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', width, height, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan)) + chunk(b'IEND', b'')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=ROOT/'research/evidence/original-recovery')
    args = parser.parse_args()
    sys.path.insert(0, str(args.source/'tools'))
    import ps2_container
    import ps2_sections
    from corpus_binding import Baseline
    baseline = Baseline(args.source/'games/ford-racing-2')
    expected = {e.path.lstrip('/'): e for e in baseline.entries('.ps2;1')}
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    code_pins = {n: digest((args.source/'tools'/n).read_bytes()) for n in
                 ['ps2_container.py','ps2_texture_indices.py','ps2_sections.py','format_contracts.py','corpus_binding.py']}
    formats, profiles, header_flags, counts = Counter(), Counter(), Counter(), Counter()
    cars, cards = [], []
    for folder in sorted((ROOT/'reference/ford/cars').iterdir()):
        manifest_path = folder/'manifest.json'
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text())
        model = next(folder.glob('model/*.PS2;1'))
        src = next(f for f in manifest['files'] if '/model/' in f['dst'])
        data = model.read_bytes()
        archive_bytes = expected[src['src']].load()
        if digest(data) != src['sha256'] or data != archive_bytes:
            raise ValueError(f'{folder.name}: model differs from archive or manifest')
        parsed = ps2_sections.parse(data)
        geo = parsed['geometry']
        counts['models'] += 1
        counts['geometry_records'] += geo['table']['count']
        counts['geometry_headers'] += geo['header_count']
        counts['exact_eof'] += parsed['exact_eof']
        textures = []
        for item in parsed['textures']['items']:
            rgba = ps2_container.decode_rgba(data, item)
            formats[str(item['format'])] += 1
            profiles[f"{item['format']}:{'packed' if int(item['descriptor_field'],16)&256 else 'direct'}"] += 1
            display = bytearray(rgba)
            display[3::4] = bytes(min(255, a*2) for a in rgba[3::4])
            stem = f"{item['index']:03d}-" + re.sub('[^A-Za-z0-9_.-]', '_', item['name'])
            relative = Path('textures')/folder.name/(stem+'.png')
            raw_relative = Path('textures')/folder.name/(stem+'.raw-alpha.png')
            (out/relative).parent.mkdir(parents=True,exist_ok=True)
            (out/relative).write_bytes(png_bytes(item['width'],item['height'],display))
            (out/raw_relative).write_bytes(png_bytes(item['width'],item['height'],rgba))
            record = {**item, 'rgba_sha256':digest(rgba),'png':relative.as_posix(),
                      'png_sha256':digest((out/relative).read_bytes()),'raw_alpha_png':raw_relative.as_posix(),
                      'raw_alpha_png_sha256':digest((out/raw_relative).read_bytes()),
                      'alpha_values':dict(sorted(Counter(rgba[3::4]).items()))}
            textures.append(record)
            counts['textures'] += 1
            counts['mip_levels_stored'] += item['mips']
            cards.append(f'<figure data-car="{html.escape(folder.name)}"><img loading="lazy" src="{html.escape(relative.as_posix())}" width="{item["width"]}" height="{item["height"]}"><figcaption><b>{html.escape(folder.name)}</b><br>{html.escape(item["name"])} · {item["width"]}×{item["height"]} · format {item["format"]}<br><a href="{html.escape(raw_relative.as_posix())}">stored alpha</a></figcaption></figure>')
        for h in geo['headers']:
            header_flags[f"{h['flags']:#06x}"] += 1
            counts['geometry_samples'] += h['count']
        cars.append({'code':folder.name,'source':src['src'],'sha256':digest(data),'bytes':len(data),
                     'texture_count':len(textures),'textures':textures,'geometry':geo,
                     'later_section':{'offset':parsed['later']['section_start'],'records':len(parsed['later']['records'])},
                     'exact_eof':parsed['exact_eof']})
        print(json.dumps({'car':folder.name,'textures':len(textures),'headers':geo['header_count']}),flush=True)
    result = {'provenance':baseline.provenance,'source_code_sha256':code_pins,
              'summary':dict(counts),'formats':dict(formats),'upload_profiles':dict(profiles),
              'geometry_header_flags':dict(header_flags),'cars':cars,
              'limits':['Level zero only under the static model upload contract.',
                        'Display alpha uses min(255,2*a); raw-alpha PNG and raw RGBA hash preserve stored values.',
                        'Model textures are distinct from PTG menu icons and alternative liveries.',
                        'Geometry layout and samples do not establish axes, scale, topology, UVs or material bindings.']}
    (out/'car-asset-census.json').write_text(json.dumps(result,indent=2)+'\n')
    options = ''.join(f'<option>{html.escape(c["code"])}</option>' for c in cars)
    page = '<!doctype html><meta charset="utf-8"><title>Original Ford Racing 2 model textures</title><style>body{background:#171c23;color:#eee;font:15px system-ui;margin:32px}h1{font-size:28px}select{padding:10px;font:inherit}main{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0;background:#252c36;padding:12px;max-width:512px}img{display:block;object-fit:contain;max-width:100%;height:auto;image-rendering:pixelated;background:repeating-conic-gradient(#777 0% 25%,#999 0% 50%) 0/16px 16px}figcaption{padding-top:8px;line-height:1.5}a{color:#a9d5ff}[hidden]{display:none}</style><h1>Original Ford Racing 2 model textures</h1><p>Archive-matched car containers; bounded level-zero decoding. Display alpha = min(255, 2 × stored alpha). These textures do not establish recovered meshes, menu icons or alternate liveries.</p><p><select aria-label="Car"><option value="">All 35 cars</option>'+options+'</select></p><main>'+''.join(cards)+'</main><script>document.querySelector("select").addEventListener("change",e=>document.querySelectorAll("figure").forEach(f=>f.hidden=!!e.target.value&&f.dataset.car!==e.target.value))</script>'
    (out/'texture-gallery.html').write_text(page)
    print(json.dumps({'summary':result['summary'],'formats':result['formats'],'profiles':result['upload_profiles']}),flush=True)


if __name__ == '__main__':
    main()
