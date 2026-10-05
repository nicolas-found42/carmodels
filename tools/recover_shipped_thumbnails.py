#!/usr/bin/env python3
"""Preserve archive-bound thumbnail streams and catalog; emit qualified previews.

Run with bundled Python/Pillow. Type-1 previews use Vinetto's substitute JPEG
tables and channel convention; original pixels and alpha are not established.
"""
import static_inputs
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE=static_inputs.bundle_path()
sys.path.insert(0,str(ROOT/'tools/validation-runtime/olefile'))
sys.path.insert(0,str(ROOT/'tools'))
import olefile
from PIL import Image
from corpus_binding import Baseline

OUT=ROOT/'research/evidence/continuation/source-refresh/thumbnails'
def sha(b):return hashlib.sha256(b).hexdigest()

def catalog(b):
    if len(b)<8:raise ValueError('short catalog')
    start,version,count=struct.unpack_from('<HHI',b)
    if start!=8 or version!=4 or not 0<count<1000:raise ValueError('unsupported catalog profile')
    rows=[];position=start;ids=set()
    while position<len(b):
        if position+20>len(b):raise ValueError('truncated catalog record')
        size,identity,timestamp=struct.unpack_from('<IIQ',b,position)
        if size<20 or size%2 or position+size>len(b):raise ValueError('invalid catalog span')
        if b[position+size-4:position+size]!=bytes(4):raise ValueError('missing catalog terminator')
        name=b[position+16:position+size-4].decode('utf-16-le')
        if identity in ids:raise ValueError('duplicate catalog identity')
        ids.add(identity);rows.append({'id':identity,'name':name,'timestamp':timestamp,'stream':str(identity)[::-1]})
        position+=size
    if len(rows)!=count:raise ValueError('catalog count differs')
    return rows

def preview(b,tables):
    if len(b)<70 or struct.unpack_from('<III',b)!=(12,1,len(b)-12):raise ValueError('thumbnail header mismatch')
    if b[28:32]!=b'\xff\xd8\xff\xc0' or b[-2:]!=b'\xff\xd9':raise ValueError('unsupported abbreviated JPEG')
    length=struct.unpack_from('>H',b,32)[0];scan=32+length
    if b[scan:scan+2]!=b'\xff\xda' or length!=20 or b[34]!=8 or b[39]!=4:raise ValueError('unsupported JPEG frame')
    height,width=struct.unpack_from('>HH',b,35)
    if not 0<width<=128 or not 0<height<=128:raise ValueError('thumbnail dimensions exceed profile')
    if b[40:52]!=bytes.fromhex('521100471100421100411100'):raise ValueError('unsupported JPEG channel profile')
    im=Image.open(io.BytesIO(tables['header'][:20]+tables['quantization']+b[30:scan]+tables['huffman']+b[scan:]))
    im.load()
    if im.size!=(width,height) or len(im.getbands())!=4:raise ValueError('thumbnail decode differs from frame')
    y,m,c,a=im.split()
    # Vinetto documented YMCA reorder with blank K. Preserve raw stream separately.
    return Image.merge('CMYK',(c,m,y,Image.new('L',im.size,0))).convert('RGB').transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def main():
    OUT.mkdir(exist_ok=True)
    tables={x:(OUT/'tables'/x).read_bytes() for x in ['header','quantization','huffman']}
    baseline=Baseline(SOURCE/'games/ford-racing-2');results=[]
    for entry in baseline.entries('Thumbs.db;1'):
        group=entry.path.split('/')[-2].lower()
        raw=entry.load();folder=OUT/group;folder.mkdir(exist_ok=True)
        with olefile.OleFileIO(io.BytesIO(raw),raise_defects=olefile.DEFECT_INCORRECT) as ole:
            c=ole.openstream('Catalog').read();rows=catalog(c)
            if len(ole.listdir())!=len(rows)+1:raise ValueError('uncatalogued streams')
            for row in rows:
                stream=ole.openstream(row['stream']).read()
                if len(stream)!=ole.get_size(row['stream']) or len(stream)>20000:raise ValueError('thumbnail stream bounds')
                name=row['name'].split('\\')[-1].lower().removesuffix('.psd')
                if not re.fullmatch('[a-z0-9_]+',name):raise ValueError('unsafe catalog name')
                path=folder/(name+'.stream.bin');path.write_bytes(stream)
                im=preview(stream,tables);image=folder/(name+'.reference-preview.png');im.save(image)
                row.update(stream_bytes=len(stream),stream_sha256=sha(stream),raw_path=str(path.relative_to(ROOT)),preview_path=str(image.relative_to(ROOT)),preview_sha256=sha(image.read_bytes()),dimensions=list(im.size))
            if ole.parsing_issues:raise ValueError('compound-file parsing issues')
        results.append({'source':entry.path,'source_sha256':sha(raw),'source_bytes':len(raw),'catalog_sha256':sha(c),'entries':rows})
    negative=[]
    c=bytes.fromhex('0800040001000000')+struct.pack('<IIQ',20,1,0)+bytes(4)
    for label,changed in [('count',c[:4]+struct.pack('<I',2)+c[8:]),('truncation',c[:-1]),('record_size',c[:8]+struct.pack('<I',0)+c[12:])]:
        try:catalog(changed)
        except ValueError:negative.append(label)
        else:raise ValueError('negative catalog fixture escaped')
    receipt={'provenance':baseline.provenance,'databases':results,'entries':sum(len(x['entries']) for x in results),'table_sha256':{k:sha(v) for k,v in tables.items()},'negative_catalog_controls':negative,'limits':['Raw streams and catalog filenames are archive-bound.','Preview uses Vinetto substitute JPEG tables and inferred YMCA channel convention; this is not exact original pixels or alpha.','Cached catalog paths establish cached artwork names, not game loading or final asset version.']}
    (OUT/'recovery.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'databases':len(results),'entries':receipt['entries'],'negative_catalog_controls':negative}))

if __name__=='__main__':main()
