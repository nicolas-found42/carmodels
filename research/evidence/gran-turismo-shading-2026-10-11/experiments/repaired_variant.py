"""Variant 'repaired': per-face orientation from stored normals; faces whose stored normals are
near-perpendicular to the face (|cos|<0.15) get the geometric face normal, oriented away from the LOD centroid.
Usage: python3 -I repaired_variant.py <repo> <glb out dir> [codes...]  (no codes = all simulation day cars)"""
import sys, json, pathlib, importlib.util
repo=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); want=set(sys.argv[3:])
sys.path.insert(0,str(repo/'tools'))
src=(repo/'tools/gt_model.py').read_text()
OLD_LOOP="""            for face in faces:
                base = len(positions)//3"""
OLD_IDX="""                indices.extend([base,base+2,base+1])
                if face['quad']:
                    indices.extend([base,base+3,base+2])"""
assert OLD_LOOP in src and OLD_IDX in src
NEW_LOOP="""            centre=[sum(v[i] for v in lod['vertices'])/len(lod['vertices']) for i in range(3)]
            for face in faces:
                base = len(positions)//3"""
NEW_IDX="""                k=len(face['vertices'])
                P=[positions[3*(base+j):3*(base+j)+3] for j in range(k)]
                fn=[0.0,0.0,0.0]
                for j in range(1,k-1):  # Newell-style fan sum over the polygon
                    u=[P[j][i]-P[0][i] for i in range(3)]; w=[P[j+1][i]-P[0][i] for i in range(3)]
                    c=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]]
                    fn=[fn[i]+c[i] for i in range(3)]
                raw=math.sqrt(sum(x*x for x in fn)); fl=raw or 1.0
                s=[sum(normals[3*(base+j)+i] for j in range(k)) for i in range(3)]
                sl=math.sqrt(sum(x*x for x in s))
                cos=(sum(fn[i]*s[i] for i in range(3))/fl/sl) if sl>1e-9 else 0.0
                if raw<1e-12:
                    sign=1.0  # zero-area face: keep stored normals, orientation is moot
                elif abs(cos)<0.15:
                    m=[sum(p[i] for p in P)/k-centre[i] for i in range(3)]
                    sign=1.0 if sum(fn[i]*m[i] for i in range(3))>=0 else -1.0
                    for j in range(k):
                        normals[3*(base+j):3*(base+j)+3]=[sign*x/fl for x in fn]
                else:
                    sign=1.0 if cos>0 else -1.0
                tri=[[0,1,2]]+([[0,2,3]] if face['quad'] else [])
                for t in tri:
                    t=[base+j for j in t]
                    indices.extend(t if sign>0 else [t[0],t[2],t[1]])"""
m=importlib.util.module_from_spec(importlib.util.spec_from_loader('gt_model_repaired',loader=None))
exec(compile(src.replace(OLD_LOOP,NEW_LOOP).replace(OLD_IDX,NEW_IDX),'gt_model_repaired','exec'),m.__dict__)
index=json.loads((repo/'gran-turismo/cars/index.json').read_text())
(out/'repaired').mkdir(parents=True,exist_ok=True); n=0
for car in index['cars']:
    if car['mode']!='simulation' or car.get('variant')!='day': continue
    code='GT_'+'_'.join(car['id'].split('/')).upper().replace('-','_')
    if want and code not in want: continue
    files={pathlib.Path(a['file']).suffix:(repo/'gran-turismo/cars'/a['file']).read_bytes() for a in car['assets']}
    glb,_=m.build_glb(files['.car'],files['.tex'],car['id']); (out/'repaired'/(code+'.glb')).write_bytes(glb); n+=1
print('wrote',n)
