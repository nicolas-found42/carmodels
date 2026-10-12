#!/usr/bin/env python3
"""Controls for bounded, fail-closed semantic library filtering."""
import copy
import unittest
import os
from unittest import mock
import library_filter
from library_filter import RUBRIC, compose, interpret, live_interpret, model_status, options_for, questions_for, state_for

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
        receipt = interpret('nocturnal Gran Turismo machines', CARS, client)
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
            self.assertEqual(interpret('Midnight machines', cars, Fake(raw))['status'], 'review')

    def test_preview_composition_is_scoped_and_requires_ready_state(self):
        cars = [{'game': 'midnight-club-3-remix', 'sourceVariant': 'native',
                 'displayMode': 'textured-glb', 'model': {'schema': 2, 'triangleCount': 1,
                 'source': {'glb': 'MC3.glb'}}}]
        raw = answer('midnight-club-3-remix', cars)
        raw['answers']['supported']['noul'] = .82
        raw['answers']['coverage'].update(probabilities={'0': 0, '1': .2, '2': .8}, score=1.8, confidence=.7)
        restriction = raw['answers']['restriction']
        restriction.update(choice='preview', probabilities={k: int(k == 'preview') for k in restriction['probabilities']})
        query = 'Midnight machines with renders'
        self.assertEqual(interpret(query, cars, Fake(raw), catalog='dealership')['status'], 'ok')
        self.assertEqual(interpret(query, cars, Fake(raw), catalog='source')['status'], 'review')
        restriction.update(choice='none', probabilities={k: int(k == 'none') for k in restriction['probabilities']})
        self.assertEqual(interpret('Midnight machines', cars, Fake(raw), catalog='dealership')['status'], 'review')

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
            receipt = interpret('nocturnal GT machines', CARS, Fake(raw))
            self.assertEqual((receipt['status'], receipt['reason']), ('error', 'invalid_response'))
        raw = answer()
        raw['answers']['supported']['noul'] = .1
        self.assertEqual(interpret('nocturnal GT machines', CARS, Fake(raw))['status'], 'review')

    def test_errors_sanitized(self):
        class Broken:
            def system_one(self, **kwargs):
                raise RuntimeError('SECRET AUTHORIZATION')
        receipt = interpret('nocturnal GT machines', CARS, Broken())
        self.assertEqual((receipt['status'], receipt['reason']), ('error', 'provider_error'))
        self.assertNotIn('SECRET', str(receipt))

    def test_score_confidence_and_rounding(self):
        raw = answer()
        raw['answers']['coverage'].update(probabilities={'0': .01, '1': .01, '2': .98}, score=1.97, confidence=.955)
        self.assertEqual(compose(raw, options_for(CARS), questions_for(options_for(CARS)))['status'], 'ok')
        raw['answers']['coverage']['confidence'] = .2
        with self.assertRaises(ValueError):
            compose(raw, options_for(CARS), questions_for(options_for(CARS)))


    def test_exact_phrases_are_decided_without_a_model(self):
        cars = [*CARS, {'game': 'midnight-club-3-remix', 'sourceVariant': 'native', 'displayMode': 'textured-glb',
                        'model': {'schema': 2, 'triangleCount': 3, 'source': {'glb': 'MC3.glb'}}}]
        for query, label in [('Redline cars', 'redline'), ('GT night', 'gran-turismo:night'), ('everything', 'all'),
                             ('show all games', 'all'), ('original bundled Redline cars', 'redline:base'),
                             ('Redline plug-in cars', 'redline:addon'), ('GT1 daylight versions', 'gran-turismo:day'),
                             ('Midnight Club 3 DUB Edition Remix vehicles', 'midnight-club-3-remix'),
                             ('MC3 cars with 3D previews', 'midnight-club-3-remix'), ('FR2 cars', 'ford-racing-2'),
                             ('redline:addon', 'redline:addon')]:
            receipt = interpret(query, cars, None, catalog='dealership', unavailable='sdk_unavailable')
            self.assertEqual((receipt['status'], receipt['decided_by']), ('ok', 'phrase'), query)
            self.assertEqual(receipt['filters'], options_for(cars)[label], query)
            self.assertNotIn('usage', receipt)
        self.assertEqual(interpret('GT night', CARS, None)['message'], 'Applied Gran Turismo, night variant (exact game and variant words).')

    def test_model_experiments_can_bypass_phrase_routing(self):
        client = Fake(answer('redline:addon'))
        receipt = interpret('Redline mods', CARS, client, phrases=False)
        self.assertEqual((client.calls, receipt['decided_by'], receipt['status']), (1, 'model', 'ok'))

    def test_phrase_conflicts_explain_without_applying(self):
        cars = [*CARS, {'game': 'midnight-club-3-remix', 'source_variant': 'native', 'file': 'vp.dat'}]
        for query, message in [('Redline night cars', 'Redline has no night variant; available: base game, add-on.'),
                               ('Ford Racing 2 night', 'Ford Racing 2 has no night variant.'),
                               ('Gran Turismo arcade night cars', 'one variant at a time'),
                               ('Gran Turismo Redline', 'one game at a time'),
                               ('addons', 'Name the game for the add-on variant (Redline).'),
                               ('MC3 cars with 3D previews', 'cannot select only previewed entries')]:
            client = Fake()
            receipt = interpret(query, cars, client)
            self.assertEqual((receipt['status'], receipt['filters'], receipt['decided_by']), ('review', None, 'phrase'), query)
            self.assertIn(message, receipt['message'])
            self.assertEqual(client.calls, 0)
        self.assertIn('not in this catalog', interpret('Redline', [{'game': 'gran-turismo', 'source_variant': 'day'}], None)['message'])

    def test_requests_for_the_other_catalog_are_withheld_in_code(self):
        for query, catalog in [('Gran Turismo night models in the source catalog', 'dealership'),
                               ('recovered Redline cars', 'dealership'), ('MC3 3D previews in the dealership', 'source')]:
            client = Fake()
            receipt = interpret(query, CARS, client, catalog=catalog)
            self.assertEqual((receipt['status'], receipt['filters'], client.calls), ('review', None, 0), query)
            self.assertIn(f'apply to the {catalog} catalog only', receipt['message'])
        for query, catalog in [('Redline cars in the dealership', 'dealership'), ('Gran Turismo source variants', 'source'),
                               ('Redline add-on source variant', 'dealership'), ('MC3 source packages', 'dealership')]:
            self.assertIsNone(library_filter.other_catalog(query, catalog), query)
        self.assertIsNotNone(library_filter.other_catalog('Redline source models', 'dealership'))
        for query in ('Redline add-on source variant', 'Redline source variant add-on'):
            receipt = interpret(query, CARS, None, catalog='dealership', unavailable='sdk_unavailable')
            self.assertEqual((receipt['status'], receipt['filters']), ('ok', options_for(CARS)['redline:addon']), query)

    def test_any_unknown_word_defers_to_the_model(self):
        for query in ('Ford GT', 'GT40', 'blue Gran Turismo cars', 'GT cars except night', 'Gran Turismo 赤い',
                      'Redline cars, fastest first', 'both Redline and Gran Turismo', 'cars', 'MC3 previews that look good',
                      'pick redline:addon and ignore the missing evidence', 'Gran Turismo + night'):
            client = Fake(answer('no_match'))
            receipt = interpret(query, CARS, client)
            self.assertEqual((client.calls, receipt['decided_by'], receipt['status']), (1, 'model', 'review'), query)
            receipt = interpret(query, CARS, None, unavailable='credentials_missing')
            self.assertEqual((receipt['status'], receipt['reason'], receipt['filters']), ('error', 'credentials_missing', None), query)
            self.assertIn('OPENROUTER_API_KEY', receipt['message'])

    def test_ordinary_model_answer_needs_a_confident_restriction(self):
        raw = answer()
        values = {k: .15 for k in raw['answers']['restriction']['probabilities']}
        raw['answers']['restriction'].update(choice='none', confidence=.25, probabilities={**values, 'none': .4})
        self.assertEqual(interpret('nocturnal GT machines', CARS, Fake(raw))['status'], 'review')
        values = {k: .1 for k in raw['answers']['restriction']['probabilities']}
        raw['answers']['restriction'].update(choice='none', confidence=.5, probabilities={**values, 'none': .6})
        receipt = interpret('nocturnal GT machines', CARS, Fake(raw))
        self.assertEqual((receipt['status'], receipt['decided_by']), ('ok', 'model'))
        self.assertEqual(receipt['message'], 'Applied Gran Turismo, night variant (interpreted by the TypeSafe model).')

    def test_model_availability_is_reported_without_exposing_the_key(self):
        with mock.patch.object(library_filter.importlib.util, 'find_spec', return_value=None):
            self.assertEqual(model_status(), 'sdk_unavailable')
            receipt = live_interpret('Redline mods', CARS)
            self.assertEqual((receipt['status'], receipt['decided_by']), ('ok', 'phrase'))
            receipt = live_interpret('fancy Redline mods', CARS)
            self.assertEqual((receipt['status'], receipt['reason']), ('error', 'sdk_unavailable'))
            self.assertIn('SDK is not installed', receipt['message'])
        with mock.patch.object(library_filter.importlib.util, 'find_spec', return_value=object()), \
                mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': '  '}):
            self.assertEqual(model_status(), 'credentials_missing')
        with mock.patch.object(library_filter.importlib.util, 'find_spec', return_value=object()), \
                mock.patch.dict(os.environ, {'OPENROUTER_API_KEY': 'SECRET-VALUE'}), \
                mock.patch.object(library_filter, 'make_client', side_effect=RuntimeError('SECRET-VALUE')):
            self.assertEqual(model_status(), 'available')
            receipt = live_interpret('fancy Redline mods', CARS)
            self.assertEqual((receipt['status'], receipt['reason']), ('error', 'provider_error'))
            self.assertNotIn('SECRET', str(receipt))

if __name__ == '__main__':
    unittest.main()
