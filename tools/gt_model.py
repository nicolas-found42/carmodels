"""Bounded GT1 body LOD / CTEX decoder and static GLB exporter.

Layout corroboration: JeevesGB/GTExplorer 069ab96f8353637a9ffc5c9b23695650e288e8ea
(gtcar.py, gttex.py, gtcar_render.py; MIT notice in tools/gt1/LICENSE).
All declared body LODs are parsed; no permissive vertex/palette fallback is used.
Shared wheel templates are recovered from the source-pinned native executable.
"""
import hashlib
import json
import math
import struct
import zlib

from gt_wheels import assemble_wheels

LIMITS = [
    'Static native body LOD conversion; original game execution and rendered equivalence are unverified.',
    'Static neutral wheel assembly uses the native showroom template; steering, spin and view-dependent game rounding are not reproduced.',
    'Display policy omits wheels from body LODs whose four native anchors all exceed lateral/longitudinal body bounds by more than 0.1m; original special-asset routing is unverified.',
    'Raw UV bytes sample native 256x256 sheets following the community renderer; its OBJ UV convention differs.',
    'First source colour set is displayed; every colour set remains in the original CTEX payload.',
    'PS1 semi-transparency, illumination/paint flags and game shading are not reproduced.',
    'Shadow records are preserved in metadata and omitted from visible body scenes.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Reader:
    def __init__(self, data, offset=0):
        self.data, self.offset = data, offset

    def read(self, size):
        end = self.offset + size
        if size < 0 or end > len(self.data):
            raise ValueError(f'Truncated GT-CAR at {self.offset}: need {size} bytes')
        raw = self.data[self.offset:end]
        self.offset = end
        return raw

    def unpack(self, fmt):
        return struct.unpack(fmt, self.read(struct.calcsize(fmt)))


def parse_car(data):
    if len(data) < 128 or not data.startswith(b'@(#)GT-CAR\0'):
        raise ValueError('Invalid GT-CAR header')
    reader = Reader(data, 16)
    wheels = [reader.unpack('<4h') for _ in range(4)]
    dimensions = reader.unpack('<4H')
    reader.read(4)
    count, = reader.unpack('<H')
    reader.read(66)
    if not 1 <= count <= 8:
        raise ValueError('GT-CAR LOD count outside bound')
    lods = []
    for lod_index in range(count):
        start = reader.offset
        vc, nc, tc, qc = reader.unpack('<4H')
        gtc, gqc = reader.unpack('<2H')
        utc, uqc = reader.unpack('<2H')
        reader.read(20)
        scale, _ = reader.unpack('<2H')
        if not 1 <= vc <= 4096 or not 1 <= nc <= 4096 or any(x > 8192 for x in [tc,qc,gtc,gqc,utc,uqc]):
            raise ValueError('GT-CAR LOD geometry count outside bound')
        if not 0 <= scale <= 30:
            raise ValueError('GT-CAR scale outside bound')
        factor = 2.0 ** (scale - 16) / 4096
        vertices = [(x*factor, y*factor, -z*factor) for x,y,z,w in
                    (reader.unpack('<4h') for _ in range(vc))]
        normals = []
        for _ in range(nc):
            x,y,z,w = reader.unpack('<4h')
            length = math.sqrt(x*x+y*y+z*z)
            # Native zero normals are represented explicitly and counted below.
            normals.append((x/length,y/length,-z/length) if length else (0.0,0.0,0.0))
        faces = []
        for number, quad, textured in [(tc,False,False),(qc,True,False),(gtc,False,'gouraud'),(gqc,True,'gouraud'),(utc,False,True),(uqc,True,True)]:
            for _ in range(number):
                offset = reader.offset
                b = reader.read(16)
                refs = [b[0]+((b[1]&1)<<8), (b[1]>>1)+((b[2]&3)<<7),
                        (b[2]>>2)+((b[3]&7)<<6), b[4]+((b[5]&1)<<8)]
                nr = [((b[5]+(b[6]<<8))>>1)&511, ((b[6]+(b[7]<<8))>>3)&511,
                      (b[8]+(b[9]<<8))&511, ((b[9]+(b[10]<<8))>>2)&511]
                corners = 4 if quad else 3
                expected_type = (0x38 if quad else 0x30) if textured == 'gouraud' else (0x2c if quad else 0x24) if textured else (0x28 if quad else 0x20)
                if b[15] & 0xfc != expected_type:
                    raise ValueError(f'GT-CAR face type disagrees with group at {offset}')
                if any(v >= vc for v in refs[:corners]):
                    raise ValueError(f'GT-CAR face vertex index outside LOD at {offset}')
                if any(n >= nc for n in nr[:corners]):
                    raise ValueError(f'GT-CAR face normal index outside LOD at {offset}')
                if any(normals[n] == (0.0,0.0,0.0) for n in nr[:corners]):
                    raise ValueError(f'GT-CAR referenced zero normal at {offset}')
                face = {'vertices':refs[:corners], 'normals':nr[:corners], 'offset':offset,
                        'type':b[15], 'colour':list(b[12:15]), 'quad':quad, 'clut':None}
                if textured == 'gouraud':
                    rgb = reader.read(12 if quad else 8)
                    face['corner_colours'] = [list(b[12:15])]+[list(rgb[i:i+3]) for i in range(0,len(rgb),4)]
                elif textured:
                    uv = reader.read(12)
                    pal = struct.unpack_from('<H',uv,2)[0]
                    clut = (pal >> 4) + (pal & 63)
                    if not 0 <= clut < 16:
                        raise ValueError(f'GT-CAR CLUT outside native sheet at {offset}')
                    face.update({'clut':clut,'raw_clut':pal,'uv':[list(uv[0:2]),list(uv[4:6]),
                                                                          list(uv[8:10]),list(uv[10:12])][:corners]})
                faces.append(face)
        if not faces:
            raise ValueError('GT-CAR LOD has no polygons')
        lods.append({'index':lod_index,'offset':start,'end':reader.offset,'scale':scale,
                     'vertices':vertices,'normals':normals,'faces':faces})
        if lod_index != count-1:
            reader.read(40)
    # The shadow is a bounded 32-byte header followed by sequential four-vertex quads.
    shadow_offset = reader.offset
    zero, quads, shadow_scale, zero2 = reader.unpack('<4H')
    reader.read(24)
    if quads > 8192 or shadow_scale > 30:
        raise ValueError('GT-CAR shadow count/scale outside bound')
    reader.read(quads*4*8)
    trailing = reader.read(len(data)-reader.offset)
    return {'lods':lods,'wheels':wheels,'wheel_dimensions':dimensions,
            'shadow':{'offset':shadow_offset,'quads':quads,'scale':shadow_scale},
            'trailing_bytes':len(trailing),'trailing_sha256':sha(trailing)}


def parse_tex(data):
    if len(data) < 0x8060 or not data.startswith(b'@(#)GT-CTEX\0'):
        raise ValueError('Invalid GT-CTEX header')
    count, = struct.unpack_from('<H',data,14)
    if not 1 <= count <= 16 or len(data) != 0x8060+count*512:
        raise ValueError('GT-CTEX palette count/length differs')
    palettes = [list(struct.unpack_from('<256H',data,0x8060+i*512)) for i in range(count)]
    pixels = bytearray()
    for byte in data[0x60:0x8060]:
        pixels.extend((byte&15,byte>>4))
    return {'count':count,'colour_ids':list(data[16:16+count]),'pixels':pixels,'palettes':palettes,
            'illumination_masks':list(struct.unpack_from('<16H',data,32)),
            'paint_masks':list(struct.unpack_from('<16H',data,64))}


def png(data, clut, colour=0):
    if not 0 <= clut < 16 or not 0 <= colour < data['count']:
        raise ValueError('GT texture palette selector outside range')
    palette = data['palettes'][colour][clut*16:(clut+1)*16]
    rgba = [bytes(((c&31)<<3,((c>>5)&31)<<3,((c>>10)&31)<<3,0 if c==0 else 255)) for c in palette]
    # C-backed channel lookup keeps full-sheet corpus verification inexpensive.
    pixels = bytes(data['pixels'])
    expanded = bytearray(256*256*4)
    for channel in range(4):
        table = bytes([c[channel] for c in rgba])+bytes(240)
        expanded[channel::4] = pixels.translate(table)
    raw = b''.join(b'\0'+expanded[y*1024:(y+1)*1024] for y in range(256))
    def chunk(kind,payload):
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',256,256,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')


def srgb(v):
    return v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4


def wheel_bounds_fit(car, lod):
    """Conservative display policy for small special-asset LODs, not native routing."""
    bounds = [(min(v[i] for v in lod['vertices']), max(v[i] for v in lod['vertices'])) for i in (0,2)]
    outside = []
    for x, _, z, _ in car['wheels']:
        outside.append(any(value < low-.1 or value > high+.1
                           for value,(low,high) in zip((x/4096,-z/4096),bounds)))
    return not all(outside)


def build_glb(car_data, tex_data, identity):
    car, tex = parse_car(car_data), parse_tex(tex_data)
    binary = bytearray()
    doc = {'asset':{'version':'2.0','generator':'Bounded GT1 native body and wheel exporter'},'scene':0,
           'scenes':[],'nodes':[],'meshes':[],'accessors':[],'bufferViews':[],'buffers':[],
           'materials':[],'images':[],'textures':[],'samplers':[{'magFilter':9728,'minFilter':9728,'wrapS':33071,'wrapT':33071}],
           'extras':{'sourceId':identity,'sourceCarSha256':sha(car_data),'sourceTexSha256':sha(tex_data),
                     'sourceProfile':'gran-turismo-native-candidate','claim_limits':LIMITS,
                     'nativeWheelCentres':car['wheels'],'nativeWheelDimensions':car['wheel_dimensions'],
                     'nativeShadow':car['shadow'],'trailingBytes':car['trailing_bytes'],
                     'trailingSha256':car['trailing_sha256'],'sourceColourSetCount':tex['count'],
                     'sourceColourIds':tex['colour_ids'],'displayedColourSet':0,
                     'illuminationMasks':tex['illumination_masks'],'paintMasks':tex['paint_masks']}}
    def view(payload,target=None):
        binary.extend(b'\0'*((-len(binary))%4))
        index = len(doc['bufferViews'])
        row = {'buffer':0,'byteOffset':len(binary),'byteLength':len(payload)}
        if target:
            row['target'] = target
        doc['bufferViews'].append(row)
        binary.extend(payload)
        return index
    def accessor(values,width,kind='f',bounds=False):
        payload = struct.pack('<'+kind*len(values),*values)
        row = {'bufferView':view(payload,34963 if kind=='I' else 34962),'componentType':5125 if kind=='I' else 5126,
               'count':len(values)//width,'type':{1:'SCALAR',2:'VEC2',3:'VEC3'}[width]}
        if bounds:
            actual = [v[0] for v in struct.iter_unpack('<f',payload)]
            row.update({'min':[min(actual[j::width]) for j in range(width)],'max':[max(actual[j::width]) for j in range(width)]})
        doc['accessors'].append(row)
        return len(doc['accessors'])-1
    selectors = sorted({0} | {f['clut'] for lod in car['lods'] for f in lod['faces'] if f['clut'] is not None})
    materials = {}
    for clut in selectors:
        image = len(doc['images'])
        doc['images'].append({'bufferView':view(png(tex,clut)),'mimeType':'image/png','name':f'Native colour0 CLUT{clut}'})
        doc['textures'].append({'sampler':0,'source':image})
        materials[clut] = len(doc['materials'])
        doc['materials'].append({'name':f'Native CLUT{clut}','doubleSided':True,'alphaMode':'MASK','alphaCutoff':0.5,
                                'pbrMetallicRoughness':{'baseColorTexture':{'index':image},'metallicFactor':0,'roughnessFactor':1},
                                'extras':{'nativeCLUT':clut,'nativeColourSet':0}})
    records = []
    wheel_nodes = []
    # Native showroom calls select wheel template 0 independently of body LOD.
    # Reflect the whole assembly into the same glTF Z basis as the body.
    for wheel in assemble_wheels(car, lod=0):
        positions, normals, uvs, indices = [], [], [], []
        for quad in wheel['quads']:
            for triangle in [(quad[0], quad[1], quad[3]), (quad[3], quad[1], quad[2])]:
                vertices = [(wheel['positions'][v][0]/4096, wheel['positions'][v][1]/4096,
                             -wheel['positions'][v][2]/4096) for v in triangle]
                # Compute flat normals after the coordinate reflection; native
                # wheel packets are textured polygons without stored normals.
                vertices[1], vertices[2] = vertices[2], vertices[1]
                a = [vertices[1][i]-vertices[0][i] for i in range(3)]
                b = [vertices[2][i]-vertices[0][i] for i in range(3)]
                normal = [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
                length = math.sqrt(sum(x*x for x in normal))
                if not length:
                    raise ValueError('Degenerate native wheel triangle')
                normal = [x/length for x in normal]
                base = len(positions)//3
                for vertex, reference in zip(vertices, [triangle[0], triangle[2], triangle[1]]):
                    positions.extend(vertex)
                    normals.extend(normal)
                    uvs.extend((c+0.5)/256 for c in wheel['uv'][reference])
                indices.extend((base, base+1, base+2))
        mesh, node = len(doc['meshes']), len(doc['nodes'])
        primitive = {'attributes':{'POSITION':accessor(positions,3,bounds=True),
                                   'NORMAL':accessor(normals,3), 'TEXCOORD_0':accessor(uvs,2)},
                     'indices':accessor(indices,1,'I'),'mode':4,'material':materials[0]}
        doc['meshes'].append({'name':f'Native wheel {wheel["wheel_index"]}', 'primitives':[primitive]})
        doc['nodes'].append({'name':f'Native wheel {wheel["wheel_index"]}', 'mesh':mesh,
                             'extras':{'nativeWheelIndex':wheel['wheel_index'],'nativeTemplateLOD':0}})
        wheel_nodes.append(node)
    doc['extras']['wheelAssembly'] = {'templateLOD':0,'quadsPerWheel':31,'wheels':len(wheel_nodes),
                                      'basis':'Native CAR units /4096; entire assembly reflects Z',
                                      'pose':'Neutral showroom steering and spin'}
    for lod in car['lods']:
        groups = {}
        for face in lod['faces']:
            key = 'gouraud' if 'corner_colours' in face else face['clut'] if face['clut'] is not None else ('colour',tuple(face['colour']))
            groups.setdefault(key,[]).append(face)
        primitives = []
        for key,faces in groups.items():
            if key not in materials:
                materials[key] = len(doc['materials'])
                doc['materials'].append({'name':'Native per-corner RGB' if key == 'gouraud' else 'Native face RGB '+str(key[1]),'doubleSided':True,
                                        'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1] if key == 'gouraud' else [srgb(v/255) for v in key[1]]+[1],
                                                               'metallicFactor':0,'roughnessFactor':1}})
            positions,normals,uvs,indices,colours = [],[],[],[],[]
            for face in faces:
                base = len(positions)//3
                for corner,v in enumerate(face['vertices']):
                    positions.extend(lod['vertices'][v])
                    normals.extend(lod['normals'][face['normals'][corner]])
                    if 'corner_colours' in face:
                        # glTF vertex colours are linear; native RGB bytes are display encoded.
                        colours.extend([srgb(v/255) for v in face['corner_colours'][corner]])
                    if face['clut'] is not None:
                        uvs.extend([(c+0.5)/256 for c in face['uv'][corner]])
                # Native CAR quads follow boundary order (0,1,2),(0,2,3).
                # Z reflection reverses winding; doubleSided also preserves uncertain culling.
                indices.extend([base,base+2,base+1])
                if face['quad']:
                    indices.extend([base,base+3,base+2])
            attrs = {'POSITION':accessor(positions,3,bounds=True),'NORMAL':accessor(normals,3)}
            if colours:
                attrs['COLOR_0'] = accessor(colours,3)
            if uvs:
                attrs['TEXCOORD_0'] = accessor(uvs,2)
            primitives.append({'attributes':attrs,'indices':accessor(indices,1,'I'),'mode':4,'material':materials[key]})
        mesh = len(doc['meshes']); node = len(doc['nodes'])
        doc['meshes'].append({'name':f'LOD{lod["index"]}','primitives':primitives})
        doc['nodes'].append({'name':f'Native body LOD{lod["index"]}','mesh':mesh})
        visible_wheels = wheel_nodes if wheel_bounds_fit(car,lod) else []
        doc['scenes'].append({'name':f'LOD{lod["index"]}','nodes':[node, *visible_wheels],
                              'extras':{'wheelAssemblySuppressed':bool(wheel_nodes and not visible_wheels)}})
        records.append({'lod':lod['index'],'offset':lod['offset'],'end':lod['end'],
                        'vertices':len(lod['vertices']),'normals':len(lod['normals']),
                        'zero_normals':sum(n==(0.0,0.0,0.0) for n in lod['normals']),
                        'polygons':len(lod['faces']),'triangles':sum(2 if f['quad'] else 1 for f in lod['faces']),
                        'wheel_template_lod':0,'wheel_triangles':62*len(visible_wheels),
                        'wheel_assembly_suppressed':bool(wheel_nodes and not visible_wheels)})
    doc['buffers'] = [{'byteLength':len(binary)}]
    encoded = json.dumps(doc,separators=(',',':'),ensure_ascii=True).encode()
    encoded += b' '*((-len(encoded))%4)
    binary.extend(b'\0'*((-len(binary))%4))
    glb = struct.pack('<4sII',b'glTF',2,12+8+len(encoded)+8+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    return glb,records
