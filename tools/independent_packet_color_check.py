#!/usr/bin/env python3
"""Reparse packet color lanes and use independent SVD least squares for diagnostics."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    report_path=ROOT/'research/evidence/packet-continuation/race94-trace.json';receipt=json.loads(report_path.read_text());dump=ROOT/receipt['gs_dump']['path']
    if hashlib.sha256(dump.read_bytes()).hexdigest()!=receipt['gs_dump']['compressed_sha256']:raise ValueError('GS dump changed')
    raw=subprocess.check_output([shutil.which('zstd'),'-dc',str(dump)]);_,header=struct.unpack_from('<II',raw);state_size=struct.unpack_from('<I',raw,12)[0];cursor=8+header+state_size+8192;transfers=[]
    while cursor<len(raw):
        kind=raw[cursor];cursor+=1
        if kind==0:
            size=struct.unpack_from('<I',raw,cursor+1)[0];cursor+=5
            if cursor+size>len(raw):raise ValueError('truncated transfer')
            transfers.append(raw[cursor:cursor+size]);cursor+=size
        elif kind==1:cursor+=1
        elif kind==2:cursor+=4
        elif kind==3:cursor+=8192
        else:raise ValueError('unknown dump record')
    model=ROOT/receipt['texture_join']['model_path'];source=model.read_bytes()
    if hashlib.sha256(source).hexdigest()!=receipt['texture_join']['model_sha256']:raise ValueError('model changed')
    census=json.loads((ROOT/'research/evidence/original-recovery/car-asset-census.json').read_text());car=next(c for c in census['cars'] if c['code']=='COBRA');s=receipt['source_packet_match_summary'];paired=s['source_v4_8_to_packet_rgb_probe'];features=[];targets=[];misread=0;alpha={};tag_count=0
    for row in paired['per_tag']:
        p=transfers[row['transfer_index']];at=0;matches=[]
        while at<len(p):
            lo,hi=struct.unpack_from('<QQ',p,at);n=lo&32767;flg=(lo>>58)&3;nreg=(lo>>60)&15 or 16
            payload=n*nreg*16 if flg==0 else ((n*nreg+1)//2)*16 if flg==1 else n*16 if flg==2 else 0
            if at+16+payload>len(p):raise ValueError('truncated GIF payload')
            if flg==0 and hi==0x412 and nreg==3 and n==row['vertices']:matches.append((at,n))
            at+=16+payload
        if len(matches)!=1:raise ValueError('packet association ambiguous')
        at,n=matches[0];cols=[]
        for i in range(n):
            qword=p[at+16+(3*i+1)*16:at+32+(3*i+1)*16]
            rgba=[qword[j] for j in [0,4,8,12]];cols.append(rgba[:3]);alpha[str(rgba[3])]=alpha.get(str(rgba[3]),0)+1
            misread+=int(rgba[:3]!=list(qword[:3]))
        planes=[]
        for i in row['source_header_indices_with_byte_identical_four_byte_plane']:
            h=car['geometry']['headers'][i]['planes']['four_byte'];planes.append(source[h['offset']:h['end']])
        if len(set(planes))!=1 or len(planes[0])!=4*n or hashlib.sha256(planes[0]).hexdigest()!=row['source_four_byte_sha256']:raise ValueError('source planes differ')
        attrs=np.frombuffer(planes[0],dtype=np.int8).reshape(n,4)[:,:3];features.extend(attrs.tolist());targets.extend(cols);tag_count+=1
    x=np.asarray(features,dtype=float);y=np.asarray(targets,dtype=float);r2={};coefficients={}
    for name,features in [('signed',x),('unsigned',np.where(x<0,x+256,x))]:
        design=np.column_stack((np.ones(len(x)),features));co,_,rank,_=np.linalg.lstsq(design,y,rcond=None)
        if rank!=4:raise ValueError('rank-deficient global fit')
        predicted=design@co;score=1-((y-predicted)**2).sum(axis=0)/((y-y.mean(axis=0))**2).sum(axis=0);r2[name]=score.tolist();coefficients[name]=co.tolist()
    for i,c in enumerate('rgb'):
        if abs(r2['signed'][i]-paired['global_signed8_xyz_to_rgb_linear_r2'][c])>1e-10:raise ValueError('independent R2 differs')
        if abs(r2['unsigned'][i]-paired['global_unsigned8_lane0_2_to_rgb_linear_r2'][c])>1e-10:raise ValueError('independent control R2 differs')
    if tag_count!=105 or len(x)!=5908 or misread==0:raise ValueError('coverage/negative control differs')
    result={'reviewed_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),'independent_tags':tag_count,'independent_vertex_pairs':len(x),'packed_rgba_low_word_misread_negative':{'different_rgb_vertices':misread,'rejected':True},'alpha_counts_in_matched_tags':alpha,'independent_svd_r2':r2,'independent_svd_coefficients':coefficients,'failures':0,'limits':'Checks raw packed GIF RGBA lanes, byte-equivalent source planes, and numerical diagnostics. No live VU dispatch, lighting-branch execution or final normals proof.'}
    (ROOT/'research/evidence/packet-continuation/independent-color-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
