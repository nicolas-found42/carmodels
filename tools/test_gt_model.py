"""Independent fixture, corruption and full native-corpus controls for GT1 conversion."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from bake_models import read_glb
from export_gt_models import export
from gt_model import build_glb, parse_car, parse_tex, png, sha
from model_png import decode_png

ROOT = Path(__file__).resolve().parents[1]


def car_fixture(gouraud=False):
    data = bytearray(128)
    data[:11] = b'@(#)GT-CAR\0'
    for i, centre in enumerate([(500,1300,0,0),(3000,1300,0,0),
                                (500,1300,0,0),(3000,1300,0,0)]):
        struct.pack_into('<4h',data,16+i*8,*centre)
    struct.pack_into('<4H',data,48,900,1300,900,1300)
    struct.pack_into('<H',data,60,1)
    # Independent three-vertex face, normal0, RGB, palette0 native packet.
    header = bytearray(40)
    struct.pack_into('<8H',header,0,3,1,0,0,1 if gouraud else 0,0,0 if gouraud else 1,0)
    struct.pack_into('<H',header,36,16)
    data.extend(header)
    for vertex in [(0,0,0,0),(4096,0,0,0),(0,4096,0,0)]:
        data.extend(struct.pack('<4h',*vertex))
    data.extend(struct.pack('<4h',0,0,-4096,0))
    data.extend(bytes([0,2,8,0,0,0,0,0,0,0,0,0,255,0,0,0x30 if gouraud else 0x25]))
    if gouraud:
        data.extend(bytes([0,255,0,0,0,0,255,0]))
    else:
        data.extend(bytes([0,0,0,0,255,0,0,0,0,255,0,0]))
    data.extend(bytes(32))
    return bytes(data)


def tex_fixture():
    data = bytearray(0x8260)
    data[:12] = b'@(#)GT-CTEX\0'
    struct.pack_into('<H',data,14,1)
    data[0x60] = 0x21
    struct.pack_into('<16H',data,0x8060,0,31,31<<5,*([0]*13))
    return bytes(data)


class GTModelTests(unittest.TestCase):
    def test_independent_geometry_and_texture_pixels(self):
        c = parse_car(car_fixture())
        self.assertEqual(c['lods'][0]['vertices'],[(0.0,0.0,0.0),(1.0,0.0,0.0),(0.0,1.0,0.0)])
        self.assertEqual(c['lods'][0]['normals'],[(0.0,0.0,1.0)])
        self.assertEqual(c['lods'][0]['faces'][0]['vertices'],[0,1,2])
        self.assertEqual(c['trailing_bytes'],0)
        texture = parse_tex(tex_fixture())
        width,height,rgba = decode_png(png(texture,0))
        self.assertEqual((width,height),(256,256))
        self.assertEqual(bytes(rgba[:8]),bytes([248,0,0,255,0,248,0,255]))
        self.assertEqual(bytes(rgba[8:12]),bytes([0,0,0,0]))

    def test_gouraud_group_width_and_glb_attributes(self):
        c = parse_car(car_fixture(True))
        self.assertEqual(c['lods'][0]['faces'][0]['corner_colours'],[[255,0,0],[0,255,0],[0,0,255]])
        for gouraud in (False,True):
            glb, records = build_glb(car_fixture(gouraud),tex_fixture(),'synthetic')
            doc,binary = read_glb(glb)
            body_node = doc['nodes'][doc['scenes'][0]['nodes'][0]]
            primitive = doc['meshes'][body_node['mesh']]['primitives'][0]
            self.assertEqual('COLOR_0' in primitive['attributes'],gouraud)
            self.assertEqual('TEXCOORD_0' in primitive['attributes'],not gouraud)
            self.assertEqual(records[0]['triangles'],1)
            self.assertEqual(doc['scene'],0)
            self.assertEqual(doc['extras']['sourceCarSha256'],sha(car_fixture(gouraud)))
            self.assertTrue(binary)
            if not gouraud:
                access = doc['accessors'][primitive['attributes']['TEXCOORD_0']]
                view = doc['bufferViews'][access['bufferView']]
                self.assertEqual(struct.unpack_from('<6f',binary,view['byteOffset']),
                                 (0.5/256,0.5/256,255.5/256,0.5/256,0.5/256,255.5/256))

    def test_wheel_geometry_uv_and_scene_ownership(self):
        glb, records = build_glb(car_fixture(),tex_fixture(),'wheel-fixture')
        doc,binary = read_glb(glb)
        self.assertEqual(len(doc['scenes'][0]['nodes']),5)
        self.assertEqual(records[0]['wheel_triangles'],248)
        self.assertEqual(doc['extras']['wheelAssembly']['quadsPerWheel'],31)
        for node_id in doc['scenes'][0]['nodes'][1:]:
            primitive = doc['meshes'][doc['nodes'][node_id]['mesh']]['primitives'][0]
            self.assertEqual(doc['accessors'][primitive['indices']]['count'],186)
            material = doc['materials'][primitive['material']]
            self.assertEqual(material['extras']['nativeCLUT'],0)
            uv = doc['accessors'][primitive['attributes']['TEXCOORD_0']]
            offset = doc['bufferViews'][uv['bufferView']]['byteOffset']
            # Source table first triangle GPU order is 0,1,3; whole-assembly Z
            # reflection reverses it to 0,3,1. These are native packed texels.
            self.assertEqual(struct.unpack_from('<6f',binary,offset),
                             tuple((c+.5)/256 for c in (5,56,7,48,26,56)))

    def test_corruption_controls(self):
        original = car_fixture()
        for offset,packed,reason in [(60,struct.pack('<H',9),'LOD count'),(128,struct.pack('<H',65535),'geometry count'),
                                     (164,struct.pack('<H',31),'scale'),(200,b'\xff\x01','vertex index'),
                                     (207,b'\x0f','normal index'),(192,bytes(8),'zero normal'),
                                     (215,b'\x99','face type'),(218,struct.pack('<H',65535),'CLUT')]:
            bad = bytearray(original);bad[offset:offset+len(packed)] = packed
            with self.assertRaisesRegex(ValueError,reason):
                parse_car(bytes(bad))
        with self.assertRaisesRegex(ValueError,'Truncated'):
            parse_car(original[:-1])
        with self.assertRaisesRegex(ValueError,'Invalid GT-CAR'):
            parse_car(b'junk'+original)
        for bad in [tex_fixture()[:-1],tex_fixture()+b'x']:
            with self.assertRaisesRegex(ValueError,'palette count/length'):
                parse_tex(bad)
        bad = bytearray(tex_fixture());struct.pack_into('<H',bad,14,17)
        with self.assertRaisesRegex(ValueError,'palette count/length'):
            parse_tex(bad)

    def test_export_rederive_and_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'native';output=root/'glbs';source.mkdir()
            for name,data in [('model.car',car_fixture()),('textures.tex',tex_fixture())]:
                (source/name).write_bytes(data)
            assets=[{'file':name,'decoded_bytes':len(data),'sha256':sha(data)} for name,data in
                    [('model.car',car_fixture()),('textures.tex',tex_fixture())]]
            index={'game':'gran-turismo','cars':[{'id':'simulation/test/day','code':'test','mode':'simulation','variant':'day','assets':assets}]}
            (source/'index.json').write_text(json.dumps(index))
            self.assertEqual(export(source,output)['models'],1)
            export(source,output,True)
            exported=output/'simulation/test/day.glb';exported.write_bytes(exported.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError,'byte comparison'):
                export(source,output,True)
            (source/'model.car').write_bytes(car_fixture()+b'x')
            with self.assertRaisesRegex(ValueError,'extraction pin'):
                export(source,output)
            index['cars'][0]['assets'][0]['file']='../model.car'
            (source/'index.json').write_text(json.dumps(index))
            with self.assertRaisesRegex(ValueError,'relative profile'):
                export(source,output)

    def test_real_native_corpus_complete_lods(self):
        source=ROOT/'gran-turismo/cars'
        index=json.loads((source/'index.json').read_text())
        models=lods=gouraud=0
        for row in index['cars']:
            files={Path(a['file']).suffix:(source/a['file']).read_bytes() for a in row['assets']}
            for asset in row['assets']:
                data=files[Path(asset['file']).suffix]
                self.assertEqual((len(data),sha(data)),(asset['decoded_bytes'],asset['sha256']),row['id'])
            car=parse_car(files['.car']);parse_tex(files['.tex']);models+=1;lods+=len(car['lods'])
            exported = ROOT/'dealership/public/gran-turismo'/f"{row['id']}.glb"
            doc, _ = read_glb(exported.read_bytes())
            self.assertEqual(doc['extras']['sourceCarSha256'],sha(files['.car']))
            self.assertEqual(doc['extras']['sourceTexSha256'],sha(files['.tex']))
            self.assertEqual(doc['extras']['wheelAssembly']['wheels'],4)
            self.assertEqual(len([n for n in doc['nodes'] if 'nativeWheelIndex' in n.get('extras',{})]),4)
            special = row['id'].split('/')[1]
            self.assertEqual([len(s['nodes'])-1 for s in doc['scenes']],
                             {'_0logn':[0,0,4], '_lcupn':[0,4,4]}.get(special,[4,4,4]),row['id'])
            for node in doc['nodes']:
                if 'nativeWheelIndex' in node.get('extras',{}):
                    primitive = doc['meshes'][node['mesh']]['primitives'][0]
                    self.assertEqual(doc['accessors'][primitive['indices']]['count'],186)
            self.assertEqual(car['trailing_bytes'],0,row['id'])
            gouraud+=sum('corner_colours' in f for lod in car['lods'] for f in lod['faces'])
            for lod in car['lods']:
                for face in lod['faces']:
                    for normal in face['normals']:
                        self.assertNotEqual(lod['normals'][normal],(0,0,0))
        self.assertEqual((models,lods,gouraud),(728,2184,1042))


if __name__ == '__main__':
    unittest.main()
