import sys, glob, json, math, statistics as st, collections
sys.path.insert(0, sys.argv[1] + '/tools')
import gt_model
root = sys.argv[1] + '/gran-turismo/cars'
cars = sorted(glob.glob(root + '/simulation/*/day/model.car'))
out = collections.Counter(); upn=[]; outw=[]; geo=[]; texl=[]; tcol=collections.Counter(); gcol=[]; fcol=[]
def lum(c): return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
for path in cars:
    car = gt_model.parse_car(open(path,'rb').read())
    tex = gt_model.parse_tex(open(path.replace('model.car','textures.tex'),'rb').read())
    lod = car['lods'][0]; V=lod['vertices']; N=lod['normals']
    cx=sum(v[0] for v in V)/len(V); cy=sum(v[1] for v in V)/len(V); cz=sum(v[2] for v in V)/len(V)
    ymax=max(v[1] for v in V); ymin=min(v[1] for v in V)
    pos=agree=top_up=top=0; tot=0
    for f in lod['faces']:
        p=[V[i] for i in f['vertices']]; n=[N[i] for i in f['normals']]
        a=[p[1][k]-p[0][k] for k in range(3)]; b=[p[2][k]-p[0][k] for k in range(3)]
        g=[a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        gl=math.sqrt(sum(x*x for x in g)) or 1; g=[x/gl for x in g]
        m=[sum(x[k] for x in n)/len(n) for k in range(3)]
        c=[sum(x[k] for x in p)/len(p) for k in range(3)]
        d=[c[0]-cx,c[1]-cy,c[2]-cz]
        tot+=1
        if sum(m[k]*d[k] for k in range(3))>0: pos+=1
        if abs(sum(m[k]*g[k] for k in range(3)))>0.5: agree+=1
        if c[1] > ymin+0.8*(ymax-ymin):
            top+=1; top_up += m[1]>0
        if f['clut'] is not None: tcol[tuple(f['colour'])]+=1
        elif 'corner_colours' in f: gcol += [lum(cc) for cc in f['corner_colours']]
        else: fcol.append(lum(f['colour']))
    outw.append(pos/tot); geo.append(agree/tot); upn.append(top_up/max(top,1))
    # Whole-sheet texel luminance estimate: every non-transparent sheet pixel, weighted by how often faces use
    # each CLUT. Face UVs are not applied, so pixels no face samples are included.
    pal=tex['palettes'][0]
    vals=[]
    for clut in range(16):
        P=pal[clut*16:(clut+1)*16]
        rgb=[((c&31)<<3,((c>>5)&31)<<3,((c>>10)&31)<<3) for c in P]
        vals.append([lum(x) for x in rgb])
    hist=collections.Counter(tex['pixels'])
    used=collections.Counter(f['clut'] for f in lod['faces'] if f['clut'] is not None)
    s=w=0
    for clut,cnt in used.items():
        for idx,h in hist.items():
            if pal[clut*16+idx]==0: continue
            s+=vals[clut][idx]*h*cnt; w+=h*cnt
    if w: texl.append(s/w)
def q(x): x=sorted(x); return dict(min=round(x[0],3), p10=round(x[len(x)//10],3), median=round(st.median(x),3), p90=round(x[9*len(x)//10],3), max=round(x[-1],3))
print(json.dumps({
 'cars_day_lod0': len(cars),
 'stored_normals_outward_fraction': q(outw),
 'stored_normals_parallel_to_geometry_fraction': q(geo),
 'top20pct_faces_with_upward_stored_normal': q(upn),
 'texel_luma_0_255_weighted_by_use': q(texl),
 'textured_face_colour_bytes_top5': [(list(k),v) for k,v in tcol.most_common(5)],
 'textured_face_colour_distinct': len(tcol),
 'gouraud_corner_luma_0_255': q(gcol) if gcol else None,
 'flat_face_luma_0_255': q(fcol) if fcol else None,
}, indent=1))
