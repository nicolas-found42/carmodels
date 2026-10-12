import sys, glob, json, struct, statistics as st, collections, math
paths = sorted(glob.glob(sys.argv[1] + '/dealership/dealership/models/GT_SIMULATION_*_DAY.glb'))
def load(p):
    d=open(p,'rb').read(); n=struct.unpack_from('<I',d,12)[0]
    doc=json.loads(d[20:20+n]); o=20+n; bl=struct.unpack_from('<I',d,o)[0]; return doc, d[o+8:o+8+bl]
def acc(doc,bin,i):
    a=doc['accessors'][i]; v=doc['bufferViews'][a['bufferView']]
    w={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]; f={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    off=v.get('byteOffset',0)+a.get('byteOffset',0)
    flat=struct.unpack_from('<%d%s'%(a['count']*w,f),bin,off)
    return [flat[k*w:(k+1)*w] for k in range(a['count'])] if w>1 else list(flat)
agree_f=[]; mats=collections.Counter(); area_by=collections.Counter(); col=[]
for p in paths:
    doc,bin=load(p)
    scene=doc['scenes'][doc.get('scene',0)]['nodes']
    nodes=set(); stack=list(scene)
    while stack:
        i=stack.pop(); nodes.add(i); stack+=doc['nodes'][i].get('children',[])
    agree=tot=0
    for i in nodes:
        nd=doc['nodes'][i]
        if 'mesh' not in nd: continue
        if 'wheel' in nd.get('name','').lower(): continue
        for pr in doc['meshes'][nd['mesh']]['primitives']:
            P=acc(doc,bin,pr['attributes']['POSITION']); N=acc(doc,bin,pr['attributes']['NORMAL']); I=acc(doc,bin,pr['indices'])
            m=doc['materials'][pr['material']]; name=m.get('name','')
            kind='textured' if 'baseColorTexture' in m.get('pbrMetallicRoughness',{}) else ('gouraud' if 'per-corner' in name else 'flat:'+','.join('%.3f'%x for x in m['pbrMetallicRoughness']['baseColorFactor'][:3]))
            if 'COLOR_0' in pr['attributes']: col += [sum(c)/3 for c in acc(doc,bin,pr['attributes']['COLOR_0'])]
            for t in range(0,len(I),3):
                a,b,c=(P[I[t]],P[I[t+1]],P[I[t+2]])
                u=[b[k]-a[k] for k in range(3)]; v=[c[k]-a[k] for k in range(3)]
                g=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                area=math.sqrt(sum(x*x for x in g))/2
                n=[sum(N[I[t+j]][k] for j in range(3)) for k in range(3)]
                tot+=area; agree += area if sum(g[k]*n[k] for k in range(3))>0 else 0
                area_by['textured' if kind=='textured' else 'gouraud' if kind=='gouraud' else ('flat-black' if kind=='flat:0.000,0.000,0.000' else 'flat-other')]+=area
            mats[(kind if not kind.startswith('flat') else 'flat', m['pbrMetallicRoughness'].get('metallicFactor'), m['pbrMetallicRoughness'].get('roughnessFactor'), m.get('doubleSided'), 'KHR_materials_unlit' in m.get('extensions',{}))]+=1
    agree_f.append(agree/tot if tot else 0)
q=lambda x:(lambda s:dict(min=round(s[0],3),p10=round(s[len(s)//10],3),median=round(st.median(s),3),p90=round(s[9*len(s)//10],3),max=round(s[-1],3)))(sorted(x))
T=sum(area_by.values())
print(json.dumps({'glbs':len(paths),
 'area_fraction_ccw_front_agrees_with_vertex_normal':q(agree_f),
 'cars_where_less_than_half_agree':sum(a<0.5 for a in agree_f),
 'surface_area_share':{k:round(v/T,3) for k,v in area_by.items()},
 'material_kinds(kind,metallic,roughness,doubleSided,unlit)':[[list(k),v] for k,v in mats.most_common()],
 'COLOR_0_mean_linear':q(col) if col else None},indent=1))
