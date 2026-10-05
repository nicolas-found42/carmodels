#!/usr/bin/env python3
"""Independently execute pinned rotation-building EE words and compare matrix order.

This is a host numerical reconstruction, not a claim of bit-exact EE/VU hardware.
The VCALLMS polynomial model and original instruction bytes remain explicit inputs.
"""
import static_inputs
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE = static_inputs.bundle_path()
EXPORT = SOURCE/'.scratch/mesh/codex-audit/frontier-3845-01/types-t2/export-5454-po'
ELF = SOURCE/'games/ford-racing-2/extracted/SLES_517.05'
REGISTERS = 'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split()


def decode_word(payload, address):
    """Decode only the EE instruction subset used here; reject unknown words."""
    if len(payload) != 4:raise ValueError('instruction must be one word')
    w, = struct.unpack('<I', payload)
    op,rs,rt,rd,sa,fn = w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,(w>>6)&31,w&63
    imm=w&65535; signed=imm if imm<32768 else imm-65536
    r=REGISTERS
    if op in [0x31,0x39,0x36,0x3e,0x1f]:
        name,prefix={0x31:('lwc1','f'),0x39:('swc1','f'),0x36:('lqc2','vf'),0x3e:('sqc2','vf'),0x1f:('sq',None)}[op]
        return f'{name} {prefix+str(rt) if prefix else r[rt]},{hex(signed)}({r[rs]})'
    if op==0x11:
        if rs in [0,4] and (w&2047)==0:return f'{"mfc1" if rs==0 else "mtc1"} {r[rt]},f{rd}'
        if rs==16 and fn in [0,1,2,7]:
            name={0:'add.S',1:'sub.S',2:'mul.S',7:'neg.S'}[fn]
            return f'{name} f{sa},f{rd}'+('' if fn==7 else f',f{rt}')
    if op==0x1c:
        name={(8,18):'pextlw',(40,18):'pextuw',(41,30):'pexcw',(9,31):'prot3w',(9,14):'pcpyld'}.get((fn,sa))
        if name:
            if name in ['pexcw','prot3w'] and rs!=0:raise ValueError('unexpected MMI unary field')
            return f'{name} {r[rd]},'+(f'{r[rt]}' if name in ['pexcw','prot3w'] else f'{r[rs]},{r[rt]}')
    if op==0x12:
        if rs in [1,5] and (w&2047) in [0,1]:return f'{"qmfc2.I" if rs==1 else "qmtc2"} {r[rt]},vf{rd}'
        if (w&0xffe007ff)==0x4a000378:return f'vcallms {hex((w>>6)&0x7fff)}'
        if (w&0xfe0007ff)==0x4a00033c:
            mask=(w>>21)&15
            if mask in [1,15]:return f'vmove.{"w" if mask==1 else "xyzw"} vf{rt},vf{rd}'
    if op==0 and fn==45 and rt==0 and sa==0:return f'move {r[rd]},{r[rs]}'
    if op==15 and rs==0:return f'lui {r[rt]},{hex(imm)}'
    if op==9:return f'addiu {r[rt]},{r[rs]},{hex(signed)}'
    if op==4 and rs==rt==0:return f'b 0x{address+4+signed*4:08x}'
    raise ValueError(f'unsupported instruction word {w:08x} at {address:08x}')


def bind_elf(instructions, elf):
    phoff=struct.unpack_from('<I',elf,28)[0];stride,count=struct.unpack_from('<HH',elf,42)
    loads=[]
    for i in range(count):
        kind,offset,va,_,size,*_=struct.unpack_from('<8I',elf,phoff+i*stride)
        if kind==1:loads.append((va,va+size,offset))
    for ins in instructions:
        address=int(ins['address'],16);payload=bytes.fromhex(ins['bytes'])
        matches=[x for x in loads if x[0]<=address and address+4<=x[1]]
        if len(matches)!=1 or len(payload)!=4:raise ValueError('instruction ELF span invalid')
        start,end,offset=matches[0]
        if elf[offset+address-start:offset+address-start+4]!=payload:raise ValueError('instruction differs from ELF')
        if decode_word(payload,address)!=ins['text'].lstrip('_'):raise ValueError('disassembly differs from decoded instruction word')


def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def real(x):return struct.unpack('<f',struct.pack('<I',x&0xffffffff))[0]


def analytical(a,b,c):
    # Columns of R_y(a) R_x(b) R_z(c), in the original coordinate axes.
    sx,cx,sy,cy,sz,cz = math.sin(a),math.cos(a),math.sin(b),math.cos(b),math.sin(c),math.cos(c)
    return [[cz*cx+sz*sx*sy,sz*cy,sz*cx*sy-cz*sx,0],
            [-sz*cx+cz*sx*sy,cz*cy,sz*sx+cz*cx*sy,0],
            [cy*sx,-sy,cy*cx,0],[0,0,0,1]]


def execute(instructions,angles,vu_model,mutable=False):
    # The branch-likely delay at229710 loads angle1 before the mutable span.
    f={'f1':f32(angles[1])} if mutable else {}
    g={'zero':[0]*4,'a0':[0]*4};memory={};vf={0:[0.,0.,0.,1.]}
    def operand(x):
        offset,base=x[:-1].split('(')
        return int(offset,0),base
    for ins in instructions:
        text=decode_word(bytes.fromhex(ins['bytes']),int(ins['address'],16))
        if text!=ins['text'].lstrip('_'):raise ValueError('instruction text differs from word')
        mnemonic,rest=text.split(' ',1)
        args=rest.split(',')
        if mnemonic=='lwc1':
            offset,base=operand(args[1])
            if base=='s0':f[args[0]]=f32(angles[(offset-0x18)//4])
            elif base=='s3' and offset in [0x20,0x24,0x28]:f[args[0]]=f32(angles[(offset-0x20)//4])
            elif mutable and ((base=='at' and offset==0x3560) or (base=='s3' and offset==0x2c)):f[args[0]]=1.0
            else:raise ValueError('unexpected source address')
        elif mnemonic=='neg.S':f[args[0]]=-f[args[1]]
        elif mnemonic in ['mul.S','add.S','sub.S']:
            x,y=f[args[1]],f[args[2]]
            f[args[0]]=f32(x*y if mnemonic=='mul.S' else x+y if mnemonic=='add.S' else x-y)
        elif mnemonic=='mfc1':g[args[0]]=[bits(f[args[1]]),0,0,0]
        elif mnemonic=='mtc1':f[args[1]]=real(g[args[0]][0])
        elif mnemonic=='move':g[args[0]]=g[args[1]].copy()
        elif mnemonic=='pextlw':
            r,t=g[args[1]],g[args[2]];g[args[0]]=[t[0],r[0],t[1],r[1]]
        elif mnemonic=='pextuw':
            r,t=g[args[1]],g[args[2]];g[args[0]]=[t[2],r[2],t[3],r[3]]
        elif mnemonic=='pexcw':
            t=g[args[1]];g[args[0]]=[t[0],t[2],t[1],t[3]]
        elif mnemonic=='prot3w':
            t=g[args[1]];g[args[0]]=[t[1],t[2],t[0],t[3]]
        elif mnemonic=='pcpyld':g[args[0]]=g[args[2]][:2]+g[args[1]][:2]
        elif mnemonic=='qmtc2':vf[int(args[1][2:])]=[real(x) for x in g[args[0]]]
        elif mnemonic=='qmfc2.I':g[args[0]]=[bits(x) for x in vf[int(args[1][2:])]]
        elif mnemonic=='vcallms':
            if args[0]!='0x4d':raise ValueError('unexpected VU entry')
            x=vf[16];vf[16]=list(vu_model.run(x[0],tuple(x[1:]))[0])
        elif mnemonic=='vmove.xyzw':vf[int(args[0][2:])]=vf[int(args[1][2:])].copy()
        elif mnemonic=='vmove.w':vf[int(args[0][2:])][3]=vf[int(args[1][2:])][3]
        elif mnemonic=='lqc2' and mutable and args==['vf1','0x10(s3)']:vf[1]=[0.,0.,0.,1.]
        elif mutable and mnemonic=='lui' and args==['t3','0x7000']:pass
        elif mutable and mnemonic=='addiu' and args==['t1','t3','0x3020']:pass
        elif mutable and mnemonic=='lui' and args==['at','0x7000']:pass
        elif mutable and mnemonic=='swc1' and args==['f11','-0x6bf8(gp)']:pass
        elif mnemonic in ['sq','sqc2']:
            offset,base=operand(args[1])
            if base!=('t1' if mutable else 't0'):raise ValueError('unexpected matrix store')
            memory[offset]=[real(x) for x in g[args[0]]] if mnemonic=='sq' else vf[int(args[0][2:])].copy()
        elif mnemonic=='b':pass # End-of-span branch; its store delay slot is included.
        else:raise ValueError('unsupported instruction '+text)
    return [memory[i] for i in [0,16,32,48]]


def main():
    raw=(EXPORT/'inventory.json').read_bytes();inv=json.loads(raw)
    receipt=json.loads((ROOT/'research/evidence/continuation/source-refresh/refresh-identity.json').read_text())
    if hashlib.sha256(raw).hexdigest()!=receipt['inventory_sha256']:raise ValueError('inventory changed')
    f=next(f for f in inv['functions'] if f['entry']=='002296c8')
    span=[i for i in f['instructions'] if 0x229780<=int(i['address'],16)<=0x229898]
    mutable_span=[i for i in f['instructions'] if 0x2298a0<=int(i['address'],16)<=0x2299e0]
    elf=ELF.read_bytes()
    if hashlib.sha256(elf).hexdigest()!=receipt['executable_sha256']:raise ValueError('ELF changed')
    bind_elf(span+mutable_span,elf)
    model_path=ROOT/'tools/vu/vu268_reference.py'
    spec=importlib.util.spec_from_file_location('source_vu_reference',model_path)
    model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
    rng=random.Random(51705)
    probes=[(0.,0.,0.),(math.pi/2,0,0),(0,math.pi/2,0),(0,0,math.pi/2),(.31,-.62,.93)]
    probes += [tuple(rng.uniform(-math.pi,math.pi) for _ in range(3)) for _ in range(1000)]
    errors=[];negative=[]
    for angles in probes:
        observed=execute(span,angles,model);expected=analytical(*angles)
        errors.append(max(abs(x-y) for col,other in zip(observed,expected) for x,y in zip(col,other)))
        observed_mutable=execute(mutable_span,angles,model,mutable=True)
        if observed_mutable!=observed:raise ValueError('mutable rotation path differs from fixed-node path')
        if max(map(abs,angles))>0:
            wrong=analytical(angles[1],angles[0],angles[2])
            negative.append(max(abs(x-y) for col,other in zip(observed,wrong) for x,y in zip(col,other))>1e-4)
    if max(errors)>8e-6:raise ValueError('matrix-order experiment exceeds reconstruction error bound')
    controls={'zero_identity':max(abs(x-y) for col,other in zip(execute(span,(0,0,0),model),analytical(0,0,0)) for x,y in zip(col,other))<1e-6,
              'first_angle_y_axis':abs(execute(span,(math.pi/2,0,0),model)[0][2]+1)<1e-5,
              'second_angle_x_axis':abs(execute(span,(0,math.pi/2,0),model)[1][2]-1)<1e-5,
              'third_angle_z_axis':abs(execute(span,(0,0,math.pi/2),model)[0][1]-1)<1e-5,
              'swapped_axes_rejected':sum(negative)>=1000}
    mutations=[('angle_load','00229790','lwc1 f2,0x1c(s0)','1c0002c6'),
               ('lane_shuffle','002297ac','prot3w v1,v1','c91f0370'),
               ('matrix_column','0022988c','sq a3,0x10(t0)','1000077d')]
    mutation_results=[]
    for label,address,replacement,replacement_bytes in mutations:
        changed=[dict(i) for i in span]
        row=next(i for i in changed if i['address']==address);row['text']=replacement;row['bytes']=replacement_bytes
        try:bind_elf(changed,elf)
        except ValueError:elf_rejected=True
        else:raise ValueError('changed word escaped ELF binding')
        rejected=0
        for angles in probes[4:]:
            try:
                observed=execute(changed,angles,model);expected=analytical(*angles)
                delta=max(abs(x-y) for col,other in zip(observed,expected) for x,y in zip(col,other))
                rejected+=delta>8e-6
            except (ValueError,KeyError):rejected+=1
        mutation_results.append({'mutation':label,'fixtures':len(probes[4:]),'rejected':rejected,'elf_binding_rejected':elf_rejected})
        if rejected!=len(probes[4:]):raise ValueError('negative rotation mutation escaped')
    if not all(controls.values()):raise ValueError('rotation controls failed')
    assembly=json.loads((ROOT/'research/evidence/continuation/assembly-semantics.json').read_text())
    nodes=[n for c in assembly['cars'] for e in c['records'] for n in e['nodes']]
    output={'inventory_sha256':receipt['inventory_sha256'],'elf_sha256':receipt['executable_sha256'],
            'instructions':span,'mutable_instructions':mutable_span,'elf_bound_words':len(span+mutable_span),'word_text_consistency_checked':True,'vu_reference_path':str(model_path),
            'vu_reference_sha256':hashlib.sha256(model_path.read_bytes()).hexdigest(),
            'probes':len(probes),'mutable_path_probes':len(probes),'maximum_absolute_matrix_error':max(errors),'controls':controls,
            'mutation_controls':mutation_results,
            'serialized_nodes':len(nodes),'serialized_nonzero_rotations':sum(any(n['rotation_inputs']) for n in nodes),
            'rotation_order':'R_y(angle0) R_x(angle1) R_z(angle2); columns, original source axes',
            'limits':['Host reconstruction uses modeled VU polynomial and host binary32 EE arithmetic; no bit-exact hardware claim.',
                      'Fixed and mutable local rotation spans are checked with unit alpha/translation inputs; observed matrices in a render require separate evidence.']}
    (ROOT/'research/evidence/continuation/source-refresh/rotation-contract.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ['probes','maximum_absolute_matrix_error','controls','serialized_nodes','serialized_nonzero_rotations']}))


if __name__=='__main__':main()
