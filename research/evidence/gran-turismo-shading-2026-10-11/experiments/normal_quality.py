"""Corpus share of body area whose stored corner-normal sum is near-perpendicular to the face (|cos|<0.15), by material kind.
Usage: python3 -I normal_quality.py <glb dir>"""
import sys,json,math,struct,collections,pathlib,statistics as st
def rd(p):
    b=p.read_bytes(); n=struct.unpack_from('<I',b,12)[0]; doc=json.loads(b[20:20+n]); o=20+n; bl=struct.unpack_from('<I',b,o)[0]; return doc,b[o+8:o+8+bl]
def acc(doc,B,i):
    a=doc['accessors'][i]; v=doc['bufferViews'][a['bufferView']]; w={'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
    f={5126:'f',5125:'I'}[a['componentType']]; flat=struct.unpack_from('<%d%s'%(a['count']*w,f),B,v.get('byteOffset',0))
    return [flat[k*w:(k+1)*w] for k in range(a['count'])] if w>1 else list(flat)
per_car=[]; tot=collections.Counter(); perp=collections.Counter()
for p in sorted(pathlib.Path(sys.argv[1]).glob('*.glb')):
    doc,B=rd(p); ca=cp=0
    for i in doc['scenes'][0]['nodes']:
        nd=doc['nodes'][i]
        if 'wheel' in nd['name'].lower(): continue
        for pr in doc['meshes'][nd['mesh']]['primitives']:
            m=doc['materials'][pr['material']]; name=m['name']
            kind='textured' if 'baseColorTexture' in m['pbrMetallicRoughness'] else 'gouraud' if 'per-corner' in name else 'flat-black' if name.endswith('(0, 0, 0)') else 'flat-other'
            P=acc(doc,B,pr['attributes']['POSITION']); N=acc(doc,B,pr['attributes']['NORMAL']); I=acc(doc,B,pr['indices'])
            for t in range(0,len(I),3):
                a,bb,c=P[I[t]],P[I[t+1]],P[I[t+2]]
                u=[bb[k]-a[k] for k in range(3)]; v=[c[k]-a[k] for k in range(3)]
                g=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]; gl=math.sqrt(sum(x*x for x in g))
                s=[sum(N[I[t+j]][k] for j in range(3)) for k in range(3)]; sl=math.sqrt(sum(x*x for x in s))
                if not gl: continue
                bad = sl<1e-6 or abs(sum(g[k]*s[k] for k in range(3))/gl/sl)<0.15
                tot[kind]+=gl/2; ca+=gl/2
                if bad: perp[kind]+=gl/2; cp+=gl/2
    per_car.append(cp/ca)
s=sorted(per_car)
print(json.dumps({'cars':len(s),'perpendicular_area_share_per_car':dict(min=round(s[0],3),median=round(st.median(s),3),p90=round(s[9*len(s)//10],3),max=round(s[-1],3)),
 'cars_over_5pct':sum(x>.05 for x in s),
 'perpendicular_share_within_kind':{k:round(perp[k]/tot[k],3) for k in tot},
 'kind_share_of_perpendicular_area':{k:round(perp[k]/sum(perp.values()),3) for k in perp}},indent=1))
