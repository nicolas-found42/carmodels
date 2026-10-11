import sys, glob, collections, json
sys.path.insert(0, sys.argv[1] + '/tools'); import gt_model
t=collections.Counter(); black=collections.Counter(); tex=collections.Counter()
for path in sorted(glob.glob(sys.argv[1] + '/gran-turismo/cars/simulation/*/day/model.car')):
    car=gt_model.parse_car(open(path,'rb').read()); lod=car['lods'][0]
    for f in lod['faces']:
        t[hex(f['type'])]+=1
        if f['clut'] is None and 'corner_colours' not in f and f['colour']==[0,0,0]:
            ny=sum(lod['normals'][n][1] for n in f['normals'])/len(f['normals'])
            black['down(ny<-0.5)' if ny<-0.5 else 'up(ny>0.5)' if ny>0.5 else 'side']+=1
print(json.dumps({'gp0_command_byte_counts':dict(t.most_common()),'black_flat_faces_by_stored_normal':dict(black)},indent=1))
