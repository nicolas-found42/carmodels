"""Independent preservation, geometric controls and production-loader pilot checks."""
import copy
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from bake_models import accessor, read_glb
from refine_gt_model import (FURTHER_MODEL, MODEL, NEXT_MODEL, ROOT, SOURCE, SOURCE_SHA256, append_accessor, dot,
                             encode, enhance, enhance_further, face_normal, refine_mesh, sub)
from refine_gt_model import refine_eight, roundoff_winding


def values(doc, binary, primitive, key):
    return accessor(doc, binary, primitive['attributes'][key], 2 if key == 'TEXCOORD_0' else 3, 5126)


def fixture(angle=.3, seam=False, crease=False, nonmanifold=False):
    """Two independently indexed triangles sharing an oppositely directed edge."""
    doc = {'bufferViews': [], 'accessors': []}
    binary = bytearray()
    positions = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.),
                 (1., 0., 0.), (0., 0., 0.), (0., -1., angle)]
    triangles = [(0, 1, 2), (3, 4, 5)]
    normals = [face_normal(*(positions[i] for i in tri)) for tri in triangles]
    if crease:
        normals[1] = (0., 0., -1.)
    uv = [(x, y) for x, y, z in positions]
    if seam:
        uv[3] = (.5, .5)
    normal_values = [n for n in normals for _ in range(3)]
    if nonmanifold:
        positions += [(0., 0., 0.), (1., 0., 0.), (0., 0., 1.)]
        normal_values += [(0., -1., 0.)]*3
        uv += [(0., 0.), (1., 0.), (0., 1.)]
        triangles += [(6, 7, 8)]
    primitive = {'attributes': {k: append_accessor(doc, binary, v, 2 if k == 'TEXCOORD_0' else 3)
                               for k, v in [('POSITION', positions), ('NORMAL', normal_values), ('TEXCOORD_0', uv)]},
                 'indices': append_accessor(doc, binary, [(i,) for tri in triangles for i in tri], 1, integer=True),
                 'material': 0}
    return {'primitives': [primitive]}, doc, binary


class RefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        cls.output, cls.report = enhance(cls.source)
        cls.before, cls.oldbin = read_glb(cls.source)
        cls.after, cls.newbin = read_glb(cls.output)

    def test_pilot_identity_and_fourfold_default_scene(self):
        self.assertEqual(hashlib.sha256(self.source).hexdigest(), SOURCE_SHA256)
        self.assertEqual((self.report['originalTriangles'], self.report['enhancedTriangles']), (520, 2080))
        self.assertEqual(self.report['sourceId'], 'simulation/_afb7n')
        self.assertEqual(self.after['scene'], len(self.before['scenes']))
        # The original scenes, nodes, meshes, accessors and binary ranges are untouched.
        for key in ('scenes', 'nodes', 'meshes', 'accessors', 'bufferViews'):
            self.assertEqual(self.after[key][:len(self.before[key])], self.before[key])
        self.assertEqual(self.newbin[:len(self.oldbin)], self.oldbin)
        self.assertEqual(enhance(self.source), (self.output, self.report))

    def test_native_payload_artwork_variants_and_transforms_are_preserved(self):
        for key in ('materials', 'images', 'textures', 'samplers', 'extensions', 'extensionsUsed'):
            self.assertEqual(self.before[key], self.after[key])
        for key in ('nativeData', 'nativeSourcePayloads', 'nativeWheelCentres', 'nativeWheelDimensions', 'nativeMetadata'):
            self.assertEqual(self.before['extras'][key], self.after['extras'][key])
        self.assertEqual(len(self.after['extensions']['KHR_materials_variants']['variants']), 4)
        for old_index, new_index in zip(self.before['scenes'][0]['nodes'], self.after['scenes'][self.after['scene']]['nodes']):
            old, new = copy.deepcopy(self.before['nodes'][old_index]), copy.deepcopy(self.after['nodes'][new_index])
            old.pop('mesh'); new.pop('mesh')
            self.assertEqual(old, new)

    def test_original_samples_bounds_mappings_and_child_winding(self):
        original_nodes = self.before['scenes'][0]['nodes']
        enhanced_nodes = self.after['scenes'][self.after['scene']]['nodes']
        for oi, ni, report in zip(original_nodes, enhanced_nodes, self.report['meshes']):
            old_mesh = self.before['meshes'][self.before['nodes'][oi]['mesh']]
            new_mesh = self.after['meshes'][self.after['nodes'][ni]['mesh']]
            old_positions = [p for primitive in old_mesh['primitives']
                             for p in values(self.before, self.oldbin, primitive, 'POSITION')]
            new_positions = [p for primitive in new_mesh['primitives']
                             for p in values(self.after, self.newbin, primitive, 'POSITION')]
            for j in range(3):
                self.assertEqual(min(p[j] for p in old_positions), min(p[j] for p in new_positions))
                self.assertEqual(max(p[j] for p in old_positions), max(p[j] for p in new_positions))
            self.assertGreater(report['curvedEdges'], 0)
            self.assertLessEqual(report['maxMidpointDisplacementMetres'], report['displacementLimitMetres']+1e-12)
            for old, new in zip(old_mesh['primitives'], new_mesh['primitives']):
                self.assertEqual(old.get('extensions'), new.get('extensions'))
                for key in ('POSITION', 'TEXCOORD_0', 'COLOR_0'):
                    if key in old['attributes']:
                        a = values(self.before, self.oldbin, old, key)
                        self.assertEqual(values(self.after, self.newbin, new, key)[:len(a)], a)
                p = values(self.after, self.newbin, new, 'POSITION')
                original_p = values(self.before, self.oldbin, old, 'POSITION')
                self.assertEqual(new['material'], old['material'])
                oi_values = [v[0] for v in accessor(self.before, self.oldbin, old['indices'], 1, 5125)]
                ni_values = [v[0] for v in accessor(self.after, self.newbin, new['indices'], 1, 5125)]
                self.assertEqual(len(ni_values), len(oi_values)*4)
                for i in range(0, len(oi_values), 3):
                    normal = face_normal(*(original_p[v] for v in oi_values[i:i+3]))
                    for j in range(i*4, i*4+12, 3):
                        child = face_normal(*(p[v] for v in ni_values[j:j+3]))
                        if normal is not None:
                            self.assertIsNotNone(child)
                            self.assertGreater(dot(normal, child), 0)
                for a, b in zip(old.get('extras', {}).get('nativeFaces', []), new.get('extras', {}).get('nativeFaces', [])):
                    self.assertEqual(b['firstTriangle'], a['firstTriangle']*4)
                    self.assertEqual(b['triangleCount'], a['triangleCount']*4)
                    self.assertEqual(b['vertexIndices'], a['vertexIndices'])
                    self.assertEqual(b['sourceOffset'], a['sourceOffset'])

    def test_smooth_shared_midpoint_and_seam_crease_nonmanifold_controls(self):
        for options in ({}, {'seam': True}, {'crease': True}, {'nonmanifold': True}, {'angle': 2.}):
            with self.subTest(options=options):
                mesh, doc, binary = fixture(**options)
                old = values(doc, binary, mesh['primitives'][0], 'POSITION')
                new, report = refine_mesh(mesh, doc, binary)
                result = values(doc, binary, new['primitives'][0], 'POSITION')
                # Both source triangles emit their shared edge midpoint independently.
                self.assertEqual(result[len(old)], result[len(old)+3])
                if options:
                    self.assertEqual(result[len(old)], (.5, 0., 0.))
                else:
                    # This shared edge is a straight hinge: averaging its two
                    # face normals must not invent curvature along the hinge.
                    self.assertEqual(result[len(old)], (.5, 0., 0.))
                    normals = values(doc, binary, new['primitives'][0], 'NORMAL')
                    self.assertEqual(normals[0], normals[4])

    def test_wheel_ring_curves_between_fixed_original_samples(self):
        mesh, doc, binary = fixture(angle=0.)
        primitive = mesh['primitives'][0]
        positions = [(0., 1., 0.), (0., math.cos(.3), math.sin(.3)), (0., 0., 0.)]
        primitive['attributes']['POSITION'] = append_accessor(doc, binary, positions, 3)
        primitive['attributes']['NORMAL'] = append_accessor(doc, binary, [(1., 0., 0.)]*3, 3)
        primitive['attributes']['TEXCOORD_0'] = append_accessor(doc, binary, [(0., 0.), (1., 0.), (0., 1.)], 2)
        primitive['indices'] = append_accessor(doc, binary, [(0,), (1,), (2,)], 1, integer=True)
        new, report = refine_mesh(mesh, doc, binary, pivot=(0., 0., 0.))
        result = values(doc, binary, new['primitives'][0], 'POSITION')
        midpoint = tuple((x+y)/2 for x, y in zip(result[0], result[1]))
        self.assertEqual(result[:3], values(doc, binary, primitive, 'POSITION'))
        self.assertGreater(dot(result[3], result[3]), dot(midpoint, midpoint))
        delta = sub(result[3], midpoint)
        self.assertLessEqual(dot(delta, delta)**.5, report['displacementLimitMetres']+1e-7)

    def test_planar_surface_remains_planar(self):
        mesh, doc, binary = fixture(angle=0.)
        new, report = refine_mesh(mesh, doc, binary)
        self.assertEqual(report['curvedEdges'], 0)
        self.assertTrue(all(p[2] == 0 for p in values(doc, binary, new['primitives'][0], 'POSITION')))

    def test_same_directed_overlapping_faces_keep_separate_normals(self):
        mesh, doc, binary = fixture()
        p = mesh['primitives'][0]
        # Duplicate direction with a small tilt: incidence alone must not
        # merge these independent sheets into one smooth fan.
        positions = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.),
                     (0., 0., 0.), (1., 0., 0.), (0., 1., .2)]
        normal = face_normal(*positions[3:])
        p['attributes']['POSITION'] = append_accessor(doc, binary, positions, 3)
        p['attributes']['NORMAL'] = append_accessor(doc, binary, [(0., 0., 1.)]*3+[normal]*3, 3)
        p['attributes']['TEXCOORD_0'] = append_accessor(doc, binary, [(0., 0.), (1., 0.), (0., 1.)]*2, 2)
        new, _ = refine_mesh(mesh, doc, binary)
        normals = values(doc, binary, new['primitives'][0], 'NORMAL')
        self.assertNotEqual(normals[0], normals[3])

    def test_invalid_profile_and_indices_rejected(self):
        doc = copy.deepcopy(self.before)
        doc['extras']['sourceProfile'] = 'another-game'
        with self.assertRaisesRegex(ValueError, 'canonical GT1'):
            enhance(encode(doc, self.oldbin))
        mesh, doc, binary = fixture()
        mesh['primitives'][0]['indices'] = append_accessor(doc, binary, [(9999,), (0,), (1,)], 1, integer=True)
        with self.assertRaisesRegex(ValueError, 'indices outside'):
            refine_mesh(mesh, doc, binary)

    def test_production_javascript_loader_accepts_both_scenes_and_variants(self):
        if not shutil.which('node'):
            self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/MODEL
            path.write_bytes(self.output)
            script = """
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {parseEditableGLB} from './dealership/editable-glb.mjs';
const file=fs.readFileSync(process.argv[1]);
const {doc,meshes,colourVariants}=parseEditableGLB(file.buffer.slice(file.byteOffset,file.byteOffset+file.byteLength));
assert.equal(colourVariants.length,4);
assert.equal(doc.scenes.length,4);
let triangles=0;
for(const n of doc.scenes[doc.scene].nodes)for(const p of meshes[doc.nodes[n].mesh])triangles+=p.indices.length/3;
assert.equal(triangles,2080);
console.log('PASS production GLB loader: 2080 triangles, 4 paints, 4 scenes');
"""
            run = subprocess.run(['node', '--input-type=module', '-e', script, str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)

    def test_cli_freshness_rejects_changed_model_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, str(ROOT/'tools/refine_gt_model.py'), '--output-dir', tmp]
            subprocess.run(command, check=True, capture_output=True)
            subprocess.run(command+['--check'], check=True, capture_output=True)
            for name in (MODEL, 'receipt.json', FURTHER_MODEL, 'receipt-8x.json', NEXT_MODEL, 'receipt-133120.json'):
                path = Path(tmp)/name
                original = path.read_bytes()
                path.write_bytes(original+b'changed')
                run = subprocess.run(command+['--check'], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn('stale', run.stderr)
                path.write_bytes(original)


class EightfoldFurtherTests(unittest.TestCase):
    ITERATION = 1
    FROM_SCENE, TO_SCENE = 3, 4
    FROM_COUNT, TO_COUNT = 2080, 16640
    INPUT_HASH = '6a367cd2c59ce2c642e740dfabcead9f0c77c4828d3a5aac0d1d480da2b9df99'

    @classmethod
    def setUpClass(cls):
        cls.pilot, _ = enhance(SOURCE.read_bytes())
        cls.output, cls.report = enhance_further(cls.pilot)
        cls.before, cls.oldbin = read_glb(cls.pilot)
        cls.after, cls.newbin = read_glb(cls.output)

    def test_exact_eightfold_count_and_byte_identical_earlier_model(self):
        self.assertEqual(hashlib.sha256(self.pilot).hexdigest(), self.INPUT_HASH)
        self.assertEqual((self.report['originalTriangles'], self.report['enhancedTriangles']), (self.FROM_COUNT, self.TO_COUNT))
        self.assertEqual(self.report['recoveredTriangles'], 520)
        self.assertEqual(self.report['sourceSha256'], hashlib.sha256(self.pilot).hexdigest())
        self.assertEqual(self.after['scene'], self.TO_SCENE)
        self.assertEqual(self.newbin[:len(self.oldbin)], self.oldbin)
        for key in ('scenes', 'nodes', 'meshes', 'accessors', 'bufferViews'):
            self.assertEqual(self.after[key][:len(self.before[key])], self.before[key])
        for key in ('materials', 'images', 'textures', 'samplers', 'extensions', 'extensionsUsed'):
            self.assertEqual(self.after[key], self.before[key])
        self.assertEqual(enhance_further(self.pilot, iteration=self.ITERATION), (self.output, self.report))

    def test_all_samples_stay_in_recovered_envelope_and_parent_winding(self):
        old_nodes = self.before['scenes'][self.FROM_SCENE]['nodes']
        new_nodes = self.after['scenes'][self.TO_SCENE]['nodes']
        for oi, ni, report in zip(old_nodes, new_nodes, self.report['meshes']):
            old_mesh = self.before['meshes'][self.before['nodes'][oi]['mesh']]
            new_mesh = self.after['meshes'][self.after['nodes'][ni]['mesh']]
            old_positions = [v for p in old_mesh['primitives'] for v in values(self.before, self.oldbin, p, 'POSITION')]
            low = tuple(min(v[j] for v in old_positions) for j in range(3))
            high = tuple(max(v[j] for v in old_positions) for j in range(3))
            # Position and reference are independently rounded float32 vectors.
            # Bound their combined error from coordinate scale, rather than
            # assuming one absolute epsilon is enough for every generation.
            rounding = 2*math.sqrt(3)*max(1., *(abs(v) for v in low+high))*2**-23
            edge_samples = {}
            for old, new in zip(old_mesh['primitives'], new_mesh['primitives']):
                before = values(self.before, self.oldbin, old, 'POSITION')
                after = values(self.after, self.newbin, new, 'POSITION')
                self.assertEqual(after[:len(before)], before)
                for key in ('TEXCOORD_0', 'COLOR_0'):
                    if key in old['attributes']:
                        original = values(self.before, self.oldbin, old, key)
                        self.assertEqual(values(self.after, self.newbin, new, key)[:len(original)], original)
                info = new['extras']['enhancement']
                refs = accessor(self.after, self.newbin, info['referencePositions'], 3, 5126)
                self.assertEqual(len(after), len(refs))
                for position, reference in zip(after, refs):
                    distance = dot(sub(position, reference), sub(position, reference))**.5
                    self.assertLessEqual(distance, report['displacementLimitMetres']+rounding)
                    for j in range(3):
                        self.assertGreaterEqual(position[j], low[j])
                        self.assertLessEqual(position[j], high[j])
                original_indices = [v[0] for v in accessor(self.before, self.oldbin, old['indices'], 1, 5125)]
                indices = [v[0] for v in accessor(self.after, self.newbin, new['indices'], 1, 5125)]
                self.assertEqual(len(indices), 8*len(original_indices))
                lookup = {}
                for i in range(0, len(original_indices), 3):
                    tri = original_indices[i:i+3]
                    normal = face_normal(*(before[v] for v in tri))
                    for j in range(i*8, i*8+24, 3):
                        child = face_normal(*(after[v] for v in indices[j:j+3]))
                        if normal is not None:
                            self.assertIsNotNone(child)
                            self.assertGreater(dot(normal, child), 0)
                    for a, b in zip(tri, tri[1:]+tri[:1]):
                        edge = tuple(sorted((a, b)))
                        if edge not in lookup:
                            lookup[edge] = len(before)+len(lookup)
                        key = tuple(sorted((before[a], before[b])))
                        midpoint = after[lookup[edge]]
                        if key in edge_samples:
                            self.assertEqual(midpoint, edge_samples[key])
                        else:
                            edge_samples[key] = midpoint
                for a, b in zip(old.get('extras', {}).get('nativeFaces', []), new.get('extras', {}).get('nativeFaces', [])):
                    self.assertEqual(b['firstTriangle'], a['firstTriangle']*8)
                    self.assertEqual(b['triangleCount'], a['triangleCount']*8)

    def test_production_loader_accepts_all_three_editions(self):
        if not shutil.which('node'):
            self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/FURTHER_MODEL
            path.write_bytes(self.output)
            script = """
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {parseEditableGLB} from './dealership/editable-glb.mjs';
const file=fs.readFileSync(process.argv[1]);
const {doc,meshes,colourVariants}=parseEditableGLB(file.buffer.slice(file.byteOffset,file.byteOffset+file.byteLength));
assert.equal(colourVariants.length,4);
assert.equal(doc.scenes.length,Number(process.argv[2])+1);
assert.equal(doc.scene,Number(process.argv[2]));
for(const [scene,expected] of [[0,520],[3,2080],[4,16640],...(doc.scene===5?[[5,133120]]:[])]){
 let count=0;
 for(const n of doc.scenes[scene].nodes)for(const p of meshes[doc.nodes[n].mesh])count+=p.indices.length/3;
 assert.equal(count,expected);
}
console.log('PASS production loader: all retained editions and 4 paints');
"""
            run = subprocess.run(['node', '--input-type=module', '-e', script, str(path), str(self.TO_SCENE)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout+run.stderr)

    def test_wrong_stage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'first-stage'):
            enhance_further(SOURCE.read_bytes())
        with self.assertRaisesRegex(ValueError, 'first-stage'):
            enhance_further(self.output)

    def test_authored_normal_crease_survives_later_passes(self):
        for crease in (False, True):
            with self.subTest(crease=crease):
                mesh, doc, binary = fixture(crease=crease)
                pilot, _ = refine_mesh(mesh, doc, binary)
                further, _ = refine_eight(pilot, doc, binary)
                normals = values(doc, binary, further['primitives'][0], 'NORMAL')
                # Original vertices 0 and 4 are coincident on the shared edge.
                # First-pass geometric normals differ by less than 35 degrees,
                # even when the original authored normals specified a crease.
                # Only inherited protection can distinguish those cases later.
                if crease:
                    self.assertNotEqual(normals[0], normals[4])
                else:
                    self.assertEqual(normals[0], normals[4])


class EightfoldAgainTests(EightfoldFurtherTests):
    ITERATION = 2
    FROM_SCENE, TO_SCENE = 4, 5
    FROM_COUNT, TO_COUNT = 16640, 133120
    INPUT_HASH = '66c95f7345954c454af87e0fecd9ec75b6bf49af8a60c9b0865e7470549e2f17'

    @classmethod
    def setUpClass(cls):
        first, _ = enhance(SOURCE.read_bytes())
        cls.pilot, _ = enhance_further(first)
        cls.output, cls.report = enhance_further(cls.pilot, iteration=2)
        cls.before, cls.oldbin = read_glb(cls.pilot)
        cls.after, cls.newbin = read_glb(cls.output)

    def test_normal_fallbacks_are_recorded_and_normals_remain_unit(self):
        self.assertGreater(sum(r['normalInterpolationFallbacks'] for r in self.report['meshes']), 0)
        for node in self.after['scenes'][5]['nodes']:
            for p in self.after['meshes'][self.after['nodes'][node]['mesh']]['primitives']:
                normals = values(self.after, self.newbin, p, 'NORMAL')
                for n in normals:
                    self.assertAlmostEqual(dot(n, n), 1., places=5)
                lineage = p['extras']['enhancement']['vertexSourceIds']
                # Compact digests bound new lineage growth. Existing samples
                # retain their earlier representations and values.
                first_new = p['extras']['enhancement']['originalVertexCount']
                if lineage:
                    self.assertTrue(all(v.startswith('sha256:') and len(v) == 71 for v in lineage[first_new:]))

    def test_float32_winding_repairs_reject_resolvable_inversions(self):
        self.assertGreater(sum(r['float32WindingRepairs'] for r in self.report['meshes']), 0)
        for height, acceptable in ((1e-9, True), (1., False)):
            points = [(0., 0., 0.), (1., 0., 0.), (1., height, 0.)]
            indices = [0, 2, 1]*8
            if acceptable:
                self.assertEqual(roundoff_winding(points, points, indices, [0, 1, 2]), 8)
                self.assertEqual(indices, [0, 1, 2]*8)
            else:
                with self.assertRaisesRegex(ValueError, 'roundoff bound'):
                    roundoff_winding(points, points, indices, [0, 1, 2])

    def test_ambiguous_ancestry_is_rejected(self):
        doc = copy.deepcopy(self.before)
        doc['meshes'].append(copy.deepcopy(doc['meshes'][doc['nodes'][doc['scenes'][3]['nodes'][0]]['mesh']]))
        mesh = doc['meshes'][doc['nodes'][doc['scenes'][4]['nodes'][0]]['mesh']]
        with self.assertRaisesRegex(ValueError, 'ancestry'):
            refine_eight(mesh, doc, bytearray(self.oldbin))


if __name__ == '__main__':
    unittest.main(verbosity=2)
