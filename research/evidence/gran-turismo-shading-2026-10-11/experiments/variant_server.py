"""Serve the repo dealership read-only with experimental GT model and lighting variants.

URL layout: /<model>/<light>/<path under dealership/>
  model: current | no_swap | per_triangle | per_triangle_noblack | no_swap_noblack
  light: base | env | unlit
GT day GLBs come from <glb dir>/<model>/; cars.json hashes are rewritten to match.
dealership.html is patched to select ?car=<code>, stop auto-rotation, apply the lighting variant
and expose window.__capture() (returns a PNG data URL plus car-pixel luma statistics).
POST /save/<name>.png stores a capture in <glb dir>/../captures/.
Usage: python3 -I variant_server.py <repo> <glb dir> <port>
"""
import base64
import hashlib
import http.server
import json
import pathlib
import struct
import sys

repo, glb_dir, port = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
root = repo / 'dealership'
captures = glb_dir.parent / 'captures'
captures.mkdir(exist_ok=True)
BLACK = 'Native face RGB (0, 0, 0)'


def strip_black(glb):
    """Drop body primitives whose material is the flat 000000 colour (experiment only)."""
    n = struct.unpack_from('<I', glb, 12)[0]
    doc = json.loads(glb[20:20 + n])
    black = {i for i, m in enumerate(doc['materials']) if m.get('name') == BLACK}
    for mesh in doc['meshes']:
        mesh['primitives'] = [p for p in mesh['primitives'] if p.get('material') not in black] or mesh['primitives'][:1]
    enc = json.dumps(doc, separators=(',', ':')).encode()
    enc += b' ' * ((-len(enc)) % 4)
    rest = glb[20 + n:]
    return struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(enc) + len(rest)) + struct.pack('<I4s', len(enc), b'JSON') + enc + rest


cache = {}


def model_bytes(model, code):
    key = (model, code)
    if key not in cache:
        base, _, suffix = model.partition('_noblack') if model.endswith('_noblack') else (model, '', '')
        if base == 'current':
            data = (root / 'dealership/models' / (code + '.glb')).read_bytes()
        else:
            data = (glb_dir / base / (code + '.glb')).read_bytes()
        if model.endswith('_noblack'):
            data = strip_black(data)
        cache[key] = data
    return cache[key]


LIGHT_JS = {
    'base': '',
    # Image-based fill + filmic tone mapping + brighter ground bounce.
    'env': r"""
{const pm=new THREE.PMREMGenerator(renderer);const room=new THREE.Scene();
 const box=new THREE.Mesh(new THREE.BoxGeometry(30,14,30),new THREE.MeshBasicMaterial({color:0x6a6f78,side:THREE.BackSide}));box.position.y=6;room.add(box);
 for(const [x,y,z,w,h,c] of [[0,12.9,0,18,10,4.0],[-14.9,6,0,0.1,8,2.2],[14.9,6,0,0.1,8,2.2],[0,6,-14.9,12,6,1.6]]){
  const p=new THREE.Mesh(new THREE.BoxGeometry(w||0.1,h<1?0.1:(x?h:0.1),x?12:h),new THREE.MeshBasicMaterial({color:new THREE.Color(c,c,c)}));
  if(!x&&y>10){p.geometry=new THREE.BoxGeometry(w,0.1,h);} p.position.set(x,y,z);room.add(p);}
 scene.environment=pm.fromScene(room,0.04).texture;scene.environmentIntensity=0.9;
 renderer.toneMapping=THREE.NeutralToneMapping;renderer.toneMappingExposure=1.0;
 scene.traverse(o=>{if(o.isHemisphereLight){o.groundColor.set(0x55565a);}});}
""",
    'unlit': '',
}

UNLIT_JS = r"""
function __unlit(obj){obj.traverse(o=>{if(!o.isMesh)return;const s=[].concat(o.material);const m=s.map(x=>{
 const b=new THREE.MeshBasicMaterial({map:x.map,color:x.color,side:x.side,alphaTest:x.alphaTest,transparent:x.transparent,opacity:x.opacity,vertexColors:x.vertexColors});return b;});
 o.material=Array.isArray(o.material)?m:m[0];});}
"""

CAPTURE_JS = r"""
window.__capture=function(){renderer.render(scene,camera);const c=renderer.domElement;const url=c.toDataURL('image/png');
 const g=c.getContext('webgl2')||c.getContext('webgl');const w=c.width,h=c.height;const px=new Uint8Array(w*h*4);
 renderer.render(scene,camera);g.readPixels(0,0,w,h,g.RGBA,g.UNSIGNED_BYTE,px);
 // Car mask: re-render with only the car visible over pure magenta.
 const bg=scene.background,fog=scene.fog,vis=[];scene.children.forEach(o=>{if(o!==carMesh&&!o.isLight){vis.push([o,o.visible]);o.visible=false;}});
 scene.background=new THREE.Color(1,0,1);scene.fog=null;const tm=renderer.toneMapping;renderer.render(scene,camera);
 const mk=new Uint8Array(w*h*4);g.readPixels(0,0,w,h,g.RGBA,g.UNSIGNED_BYTE,mk);
 vis.forEach(([o,v])=>o.visible=v);scene.background=bg;scene.fog=fog;renderer.render(scene,camera);
 const L=[];for(let i=0;i<w*h;i++){const r=mk[4*i],gg=mk[4*i+1],b=mk[4*i+2];if(r===255&&gg===0&&b===255)continue;
  L.push(0.2126*px[4*i]+0.7152*px[4*i+1]+0.0722*px[4*i+2]);}
 L.sort((a,b)=>a-b);const q=p=>L.length?L[Math.min(L.length-1,Math.floor(p*L.length))]:null;
 return {url,stats:{carPixels:L.length,meanLuma:L.reduce((a,b)=>a+b,0)/Math.max(1,L.length),p10:q(.1),median:q(.5),p90:q(.9),
  darkShare:L.filter(v=>v<40).length/Math.max(1,L.length)}};};
"""


def patch_html(text, light):
    old = "await select(CARS.find(c => c.code === 'GRAN_TORINO') || CARS[0]);"
    assert old in text
    new = ("{const q=new URLSearchParams(location.search).get('car');"
           "await select(CARS.find(c => c.code === q) || CARS[0]);"
           "setRotation(false);" + ("__unlit(carMesh);" if light == 'unlit' else '') +
           "setView('reset');window.__loadFailed=!carMesh;window.__ready=true;}")
    text = text.replace(old, new)
    anchor = "scene.add(rim);"
    assert anchor in text
    return text.replace(anchor, anchor + LIGHT_JS[light] + UNLIT_JS + CAPTURE_JS, 1)


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, data, kind):
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self.path.startswith('/save/') or '..' in self.path:
            return self.send_error(404)
        body = self.rfile.read(int(self.headers['Content-Length']))
        payload = json.loads(body)
        name = pathlib.Path(self.path[6:]).name
        (captures / name).write_bytes(base64.b64decode(payload['url'].split(',', 1)[1]))
        (captures / (name + '.json')).write_text(json.dumps(payload['stats'], indent=1))
        self.send(b'ok', 'text/plain')

    def do_GET(self):
        parts = self.path.split('?', 1)[0].lstrip('/').split('/', 2)
        if len(parts) < 3 or '..' in parts[2]:
            return self.send_error(404)
        model, light, rel = parts
        rel = rel or 'dealership.html'
        target = root / rel
        if rel == 'dealership.html':
            return self.send(patch_html(target.read_text(), light).encode(), 'text/html')
        if rel == 'public/dealership/cars.json' and model != 'current':
            cars = json.loads(target.read_text())
            for c in cars:
                if c.get('game') == 'gran-turismo' and c.get('sourceVariant') == 'day':
                    c['model']['source']['sha256'] = hashlib.sha256(model_bytes(model, c['code'])).hexdigest()
            return self.send(json.dumps(cars).encode(), 'application/json')
        if rel.startswith('dealership/models/GT_SIMULATION_') and rel.endswith('_DAY.glb'):
            return self.send(model_bytes(model, pathlib.Path(rel).stem), 'model/gltf-binary')
        if not target.is_file():
            return self.send_error(404)
        kind = {'.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json',
                '.glb': 'model/gltf-binary', '.css': 'text/css', '.png': 'image/png'}.get(target.suffix, 'application/octet-stream')
        self.send(target.read_bytes(), kind)


http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
