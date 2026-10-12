"""TypeSafe adapter boundaries with a fake SDK-compatible client."""
import unittest
from generator_judge import LiveJudge, choice_reading


class FakeClient:
    def __init__(self):
        self.states = []

    def system_one(self, *, state, questions, model):
        self.states.append(state)
        answers = {}
        for key, question in questions.items():
            if question['type'] == 'choice':
                winner = 'coupe' if 'coupe' in question['criteria'] else '1970s'
                answers[key] = {'choice': winner, 'probabilities': {v: int(v == winner) for v in question['criteria']}}
            elif question['type'] == 'score':
                answers[key] = {'score': 1, 'confidence': .9, 'probabilities': {'0': 0, '1': 1, '2': 0},
                                'legend': {str(i): level for i, level in enumerate(question['criteria'])}}
            else:
                answers[key] = {'noul': .9 if key.startswith('car_') or key.endswith('_present') else .01}
        return {'answers': answers, 'usage': {'input_tokens': 1, 'output_tokens': 1}, 'model': model}


class Tests(unittest.TestCase):
    def test_excluded_class_overrides_a_positive_car_class(self):
        class OpenWheelClient(FakeClient):
            def system_one(self, **kwargs):
                response = super().system_one(**kwargs)
                response['answers']['excluded_0'] = {'noul': .98}
                return response
        entry = {'code': 'TEST', 'name': 'Vintage open-wheel racer', 'proportions': [.7, .4, .4],
                 'wheel_count': 4, 'wheel_coverage': 0., 'wheelbase': 2.5, 'track_width': 1.2,
                 'wheel_radius': .3, 'glb_sha256': 'a' * 64}
        reading = LiveJudge(OpenWheelClient()).classify([entry])['TEST']
        self.assertLess(reading['car_probability'], .15)
        self.assertEqual(reading['excluded_class_probability'], .98)

    def test_choice_accepts_floating_ties_and_rejects_a_lower_probability_choice(self):
        reading = choice_reading({'choice': 'b', 'probabilities': {'a': .5, 'b': .49999999999999994}}, ['a', 'b'])
        self.assertEqual(reading['value'], 'b')
        with self.assertRaisesRegex(ValueError, 'Invalid label'):
            choice_reading({'choice': 'b', 'probabilities': {'a': .9, 'b': .1}}, ['a', 'b'])

    def test_labels_and_requests_use_bounded_state_and_injected_provider(self):
        client = FakeClient()
        judge = LiveJudge(client)
        entry = {'code': 'TEST', 'name': 'Coupe', 'proportions': [.7, .4, .6], 'wheel_count': 4, 'wheel_coverage': 1.,
                 'wheelbase': 2.5, 'track_width': 1.4, 'wheel_radius': .3, 'glb_sha256': 'a' * 64,
                 'private_bytes': 'never send model bytes'}
        label = judge.classify([entry])['TEST']
        self.assertEqual(label['car_probability'], .9)
        self.assertEqual(label['bodyStyle']['value'], 'coupe')
        result = judge.interpret('a low 70s coupe')
        self.assertEqual(result['constraints']['era']['value'], '1970s')
        self.assertEqual(result['unsupported'], [])
        self.assertNotIn('private_bytes', str(client.states))
        self.assertEqual(client.states[-1]['request'], 'a low 70s coupe')
        with self.assertRaises(ValueError):
            judge.interpret('x' * 501)


if __name__ == '__main__':
    unittest.main()
