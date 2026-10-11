#!/usr/bin/env python3
"""Controls for bounded, fail-closed semantic library filtering."""
import copy
import unittest
from library_filter import RUBRIC, compose, interpret, options_for, questions_for, state_for

CARS = [{'game': 'ford-racing-2'}, *[{'game': 'gran-turismo', 'source_variant': v} for v in ('day', 'night', 'arcade')], *[{'game': 'redline', 'source_variant': v} for v in ('base', 'addon')]]


def answer(label='gran-turismo:night', cars=CARS):
    options = options_for(cars)
    labels = questions_for(options)['filter']['criteria']
    return {'model': 'test', 'usage': {'input_tokens': 1}, 'answers': {
        'filter': {'type': 'choice', 'choice': label, 'probabilities': {k: int(k == label) for k in labels}, 'confidence': 1},
        'supported': {'type': 'noul', 'noul': 1},
        'coverage': {'type': 'score', 'probabilities': {'0': 0, '1': 0, '2': 1}, 'score': 2,
                     'confidence': 1, 'legend': dict(enumerate(RUBRIC))},
        'restriction': {'type': 'choice', 'choice': 'none', 'confidence': 1,
                        'probabilities': {k: int(k == 'none') for k in questions_for(options)['restriction']['criteria']}}}}


class Fake:
    def __init__(self, raw=None):
        self.raw, self.calls = raw or answer(), 0

    def system_one(self, **kwargs):
        self.calls += 1
        self.request = kwargs
        return self.raw


class Tests(unittest.TestCase):
    def test_accept_and_no_match(self):
        client = Fake()
        receipt = interpret('night cars from Gran Turismo', CARS, client)
        self.assertEqual(receipt['status'], 'ok')
        self.assertEqual(receipt['filters'], {'game': 'gran-turismo', 'variant': 'night'})
        self.assertEqual(len(client.request['questions']), 4)
        self.assertEqual(interpret('red Ferraris', CARS, Fake(answer('no_match')))['status'], 'review')

    def test_redline_variants_and_unavailable_combinations(self):
        options = options_for(CARS)
        self.assertEqual(options['redline:base'], {'game': 'redline', 'variant': 'base'})
        self.assertEqual(options['redline:addon'], {'game': 'redline', 'variant': 'addon'})
        for label, query in [('redline:base', 'original Redline cars'), ('redline:addon', 'Redline mods')]:
            self.assertEqual(interpret(query, CARS, Fake(answer(label)))['filters'], options[label])
        self.assertEqual(interpret('both Redline and Gran Turismo', CARS, Fake(answer('no_match')))['status'], 'review')
        self.assertNotIn('redline:night', options)
        self.assertNotIn('gran-turismo:addon', options)
        with self.assertRaisesRegex(ValueError, 'Unknown library variant'):
            options_for([{'game': 'redline', 'source_variant': 'night'}])
        criteria = questions_for(options)['filter']['criteria']
        self.assertIn('mod', criteria['redline:addon'])
        self.assertIn('only when two games exist', criteria['all'])
        self.assertIn('all 3 games', criteria['all'])

    def test_boundaries_no_provider(self):
        for query in ('', ' '*10, 'x'*501, 'a\nb', None, {}):
            client = Fake()
            self.assertEqual(interpret(query, CARS, client)['status'], 'error')
            self.assertEqual(client.calls, 0)
        options = options_for([{'game': 'ford-racing-2', 'name': 'PRIVATE'}, {'game': 'unknown'}])
        self.assertNotIn('gran-turismo', options)
        self.assertNotIn('PRIVATE', str(options))

    def test_mc3_native_filter_and_no_preview_restriction(self):
        cars = [*CARS, {'game': 'midnight-club-3-remix', 'source_variant': 'native'}]
        options = options_for(cars)
        self.assertEqual(options['midnight-club-3-remix:native'], {'game': 'midnight-club-3-remix', 'variant': 'native'})
        criteria = questions_for(options)['filter']['criteria']
        self.assertIn('separate current catalog fact', criteria['midnight-club-3-remix:native'])
        self.assertIn('all 4 games', criteria['all'])
        raw = answer()
        labels = questions_for(options)['filter']['criteria']
        raw['answers']['filter'].update(choice='midnight-club-3-remix',
                                        probabilities={k: int(k == 'midnight-club-3-remix') for k in labels})
        self.assertEqual(interpret('MC3 Remix', cars, Fake(raw))['filters'], options['midnight-club-3-remix'])
        raw['answers']['filter'].update(choice='no_match', probabilities={k: int(k == 'no_match') for k in labels})
        self.assertEqual(interpret('MC3 cars with 3D previews', cars, Fake(raw))['status'], 'review')
        self.assertNotIn('midnight-club-3-remix:night', options)

    def test_current_preview_state_and_catalog_boundaries(self):
        native = {'game': 'midnight-club-3-remix', 'sourceVariant': 'native',
                  'displayMode': 'textured-glb', 'model': {'schema': 2, 'triangleCount': 12,
                  'source': {'glb': 'dealership/models/MC3.glb'}}}
        cars = [*CARS, native]
        options = options_for(cars)
        facts = state_for('MC3 previews', cars, options, 'dealership')['filter_facts']
        self.assertTrue(facts['midnight-club-3-remix']['all_have_preview'])
        self.assertEqual(facts['midnight-club-3-remix:native']['preview_ready'], 1)
        self.assertFalse(state_for('MC3 previews', cars, options)['filter_facts']['midnight-club-3-remix']['all_have_preview'])
        pending = {**native, 'displayMode': 'native-package'}
        mixed = [*cars, pending]
        self.assertFalse(state_for('MC3 previews', mixed, options, 'dealership')['filter_facts']['midnight-club-3-remix']['all_have_preview'])
        client = Fake(answer('midnight-club-3-remix', cars))
        self.assertEqual(interpret('MC3 previews in the dealership', cars, client, catalog='dealership')['status'], 'ok')
        self.assertEqual(client.request['state']['catalog'], 'dealership')
        self.assertNotIn('MC3.glb', str(client.request['state']))
        self.assertEqual(client.request['questions']['restriction']['type'], 'choice')
        with self.assertRaisesRegex(ValueError, 'Unknown library catalog'):
            state_for('MC3', cars, options, 'invented')
        client = Fake()
        self.assertEqual(interpret('MC3', cars, client, catalog='invented')['status'], 'error')
        self.assertEqual(client.calls, 0)

    def test_preview_policy_rejects_even_confident_wrong_support(self):
        cars = [{'game': 'midnight-club-3-remix', 'source_variant': 'native', 'file': 'vp.dat'}]
        raw = answer('midnight-club-3-remix', cars)
        restriction = raw['answers']['restriction']
        restriction.update(choice='preview', probabilities={k: int(k == 'preview') for k in restriction['probabilities']})
        self.assertEqual(interpret('MC3 previews', cars, Fake(raw))['status'], 'review')
        for kind in ('unsupported', 'other_catalog', 'unclear'):
            restriction.update(choice=kind, probabilities={k: int(k == kind) for k in restriction['probabilities']})
            self.assertEqual(interpret('MC3', cars, Fake(raw))['status'], 'review')

    def test_preview_composition_is_scoped_and_requires_ready_state(self):
        cars = [{'game': 'midnight-club-3-remix', 'sourceVariant': 'native',
                 'displayMode': 'textured-glb', 'model': {'schema': 2, 'triangleCount': 1,
                 'source': {'glb': 'MC3.glb'}}}]
        raw = answer('midnight-club-3-remix', cars)
        raw['answers']['supported']['noul'] = .82
        raw['answers']['coverage'].update(probabilities={'0': 0, '1': .2, '2': .8}, score=1.8, confidence=.7)
        restriction = raw['answers']['restriction']
        restriction.update(choice='preview', probabilities={k: int(k == 'preview') for k in restriction['probabilities']})
        self.assertEqual(interpret('MC3 previews', cars, Fake(raw), catalog='dealership')['status'], 'ok')
        self.assertEqual(interpret('MC3 previews', cars, Fake(raw), catalog='source')['status'], 'review')
        restriction.update(choice='none', probabilities={k: int(k == 'none') for k in restriction['probabilities']})
        self.assertEqual(interpret('MC3', cars, Fake(raw), catalog='dealership')['status'], 'review')

    def test_compiled_schema_readiness_and_actual_mc3_catalog(self):
        from pathlib import Path
        import json
        root = Path(__file__).resolve().parents[1]
        cars = json.loads((root / 'dealership/public/dealership/cars.json').read_text())
        mc3 = [car for car in cars if car.get('game') == 'midnight-club-3-remix']
        self.assertEqual(len(mc3), 94)
        self.assertTrue(all(car.get('displayMode') == 'textured-glb' and car['model'].get('schema') == 2 for car in mc3))
        facts = state_for('MC3 previews', cars, options_for(cars), 'dealership')['filter_facts']
        self.assertEqual(facts['midnight-club-3-remix']['preview_ready'], 94)
        self.assertTrue(facts['midnight-club-3-remix']['all_have_preview'])
        source = json.loads((root / 'dealership/public/models.json').read_text())['cars']
        self.assertFalse(state_for('MC3 previews', source, options_for(source))['filter_facts']['midnight-club-3-remix']['all_have_preview'])
        template = mc3[0]
        for model in ({'schema': 3, 'source': {'glb': 'bad.glb'}, 'triangleCount': 10},
                      {'schema': True, 'parts': [{}], 'source': {'glb': 'bad.glb'}, 'triangleCount': 10},
                      {'schema': 1, 'source': {'glb': 'bad.glb'}, 'triangleCount': 10},
                      {'schema': 2, 'source': {'glb': 'bad.glb'}, 'triangleCount': True},
                      {'schema': 2, 'source': {'glb': 'bad.dat'}, 'triangleCount': 10},
                      {'schema': 2, 'source': {'glb': 'bad.glb'}, 'triangleCount': 0}):
            row = {**template, 'model': model}
            self.assertFalse(state_for('MC3', [row], options_for([row]), 'dealership')['filter_facts']['midnight-club-3-remix']['all_have_preview'])

    def test_malformed_and_conflicting_fail_closed(self):
        mutations = [lambda r: r.update(warnings=['warning']),
                     lambda r: r['answers'].pop('supported'),
                     lambda r: r['answers']['filter'].update(choice='missing'),
                     lambda r: r['answers']['filter'].update(confidence=.4),
                     lambda r: r['answers']['coverage'].update(score=1),
                     lambda r: r['answers']['coverage'].update(legend={}),
                     lambda r: r['answers']['supported'].update(noul=float('nan')),
                     lambda r: r['answers']['filter'].update(status='failure')]
        for mutate in mutations:
            raw = copy.deepcopy(answer())
            mutate(raw)
            self.assertEqual(interpret('GT night', CARS, Fake(raw))['status'], 'error')
        raw = answer()
        raw['answers']['supported']['noul'] = .1
        self.assertEqual(interpret('GT night', CARS, Fake(raw))['status'], 'review')

    def test_errors_sanitized(self):
        class Broken:
            def system_one(self, **kwargs):
                raise RuntimeError('SECRET AUTHORIZATION')
        receipt = interpret('GT night', CARS, Broken())
        self.assertEqual(receipt['status'], 'error')
        self.assertNotIn('SECRET', str(receipt))

    def test_score_confidence_and_rounding(self):
        raw = answer()
        raw['answers']['coverage'].update(probabilities={'0': .01, '1': .01, '2': .98}, score=1.97, confidence=.955)
        self.assertEqual(compose(raw, options_for(CARS), questions_for(options_for(CARS)))['status'], 'ok')
        raw['answers']['coverage']['confidence'] = .2
        with self.assertRaises(ValueError):
            compose(raw, options_for(CARS), questions_for(options_for(CARS)))


if __name__ == '__main__':
    unittest.main()
