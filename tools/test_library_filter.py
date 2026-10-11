#!/usr/bin/env python3
"""Controls for bounded, fail-closed semantic library filtering."""
import copy
import unittest
from library_filter import RUBRIC, compose, interpret, options_for, questions_for

CARS = [{'game': 'ford-racing-2'}, *[{'game': 'gran-turismo', 'source_variant': v} for v in ('day', 'night', 'arcade')], *[{'game': 'redline', 'source_variant': v} for v in ('base', 'addon')]]


def answer(label='gran-turismo:night'):
    options = options_for(CARS)
    labels = questions_for(options)['filter']['criteria']
    return {'model': 'test', 'usage': {'input_tokens': 1}, 'answers': {
        'filter': {'type': 'choice', 'choice': label, 'probabilities': {k: int(k == label) for k in labels}, 'confidence': 1},
        'supported': {'type': 'noul', 'noul': 1},
        'coverage': {'type': 'score', 'probabilities': {'0': 0, '1': 0, '2': 1}, 'score': 2,
                     'confidence': 1, 'legend': dict(enumerate(RUBRIC))}}}


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
        self.assertEqual(len(client.request['questions']), 3)
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
