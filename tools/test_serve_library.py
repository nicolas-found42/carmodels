#!/usr/bin/env python3
"""Exercise the actual local HTTP endpoint without provider requests."""
import functools
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import library_filter
from serve_library import STARTUP, LibraryHandler


class Tests(unittest.TestCase):
    def test_completed_response_releases_filter_slot_before_next_request(self):
        for failure in (None, 'exception', 'nonfinite'):
            with self.subTest(failure=failure):
                self.check_completed_response(failure)

    def check_completed_response(self, failure):
        judgment_started, finish_judgment = threading.Event(), threading.Event()
        response_sent, finish_response = threading.Event(), threading.Event()

        class Handler(LibraryHandler):
            @staticmethod
            def judgment(query, cars, catalog='source'):
                if query == 'first':
                    judgment_started.set()
                    if not finish_judgment.wait(5):
                        raise RuntimeError('test judgment barrier timed out')
                    if failure == 'exception':
                        raise RuntimeError('test provider failure')
                    if failure == 'nonfinite':
                        return {'status': 'ok', 'filters': {'value': float('nan')}}
                return {'status': 'ok', 'message': query, 'filters': {}}

            def reply(self, status, payload):
                super().reply(status, payload)
                if status in (200, 503) and not response_sent.is_set():
                    # Client can read the complete body while the handler is
                    # still returning from its response write.
                    response_sent.set()
                    if not finish_response.wait(5):
                        raise RuntimeError('test response barrier timed out')

            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory() as folder, ThreadPoolExecutor(max_workers=1) as pool:
            (Path(folder)/'public').mkdir()
            (Path(folder)/'public/models.json').write_text(json.dumps({'cars': []}))
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=folder))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def ask(query):
                try:
                    response = urlopen(Request(f'http://127.0.0.1:{server.server_port}/api/library-filter',
                                               data=json.dumps({'query': query}).encode(),
                                               headers={'Content-Type': 'application/json'}), timeout=3)
                except HTTPError as error:
                    if error.code != 503:
                        raise
                    response = error
                with response:
                    return json.load(response)

            try:
                first = pool.submit(ask, 'first')
                self.assertTrue(judgment_started.wait(3))
                with self.assertRaises(HTTPError) as caught:
                    ask('busy')
                self.assertEqual(caught.exception.code, 429)
                caught.exception.close()
                finish_judgment.set()
                self.assertEqual(first.result(timeout=3)['status'], 'error' if failure else 'ok')
                self.assertTrue(response_sent.wait(3))
                self.assertEqual(ask('second')['message'], 'second')
            finally:
                finish_judgment.set()
                finish_response.set()
                server.shutdown()
                server.server_close()
                thread.join()

    def test_http_controls(self):
        calls = []
        class Handler(LibraryHandler):
            judgment = staticmethod(lambda q, cars, catalog='source': (calls.append((q, cars, catalog)) or
                {'status': 'ok', 'filters': {'game': 'gran-turismo', 'variant': 'night'}, 'message': 'Applied', 'raw_response': 'PRIVATE'}))
            def log_message(self, *args):
                pass
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'public').mkdir()
            (root/'public/models.json').write_text(json.dumps({'cars': [{'game': 'gran-turismo'}]}))
            (root/'public/dealership').mkdir()
            (root/'public/dealership/cars.json').write_text(json.dumps([{'game': 'midnight-club-3-remix', 'sourceVariant': 'native'}]))
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=folder))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f'http://127.0.0.1:{server.server_port}/api/library-filter'
            try:
                def request(data, headers=None, path=url):
                    return urlopen(Request(path, data=data, headers=headers or {'Content-Type': 'application/json'}), timeout=3)
                with request(b'{"query":"GT night"}') as response:
                    output = json.load(response)
                self.assertEqual(output['status'], 'ok')
                self.assertNotIn('PRIVATE', str(output))
                self.assertEqual(calls[-1][2], 'source')
                with request(b'{"query":"MC3 previews","catalog":"dealership"}') as response:
                    self.assertEqual(json.load(response)['status'], 'ok')
                self.assertEqual(calls[-1], ('MC3 previews', [{'game': 'midnight-club-3-remix', 'sourceVariant': 'native'}], 'dealership'))
                for data, headers, status in [
                    (b'{}', None, 400), (b'{bad', None, 400),
                    (b'{"query":"GT","catalog":"other"}', None, 400),
                    (b'{"query":"GT","catalog":{}}', None, 400),
                    (b'{"query":"GT","catalog":"source","extra":true}', None, 400),
                    (b'{"query":"GT"}', {'Content-Type': 'text/plain'}, 400),
                    (b'{"query":"GT"}', {'Content-Type': 'application/json', 'Origin': 'http://untrusted.test'}, 403),
                    (b'{"query":"GT"}', {'Content-Type': 'application/json', 'Host': 'attacker.test'}, 403),
                    (b'x'*2049, None, 400)]:
                    with self.assertRaises(HTTPError) as caught:
                        request(data, headers)
                    self.assertEqual(caught.exception.code, status)
                    caught.exception.close()
                Handler.api_lock.acquire()
                try:
                    with self.assertRaises(HTTPError) as caught:
                        request(b'{"query":"GT"}')
                    self.assertEqual(caught.exception.code, 429)
                    caught.exception.close()
                finally:
                    Handler.api_lock.release()
                self.assertEqual(len(calls), 2)
                with self.assertRaises(HTTPError) as caught:
                    request(b'{}', path=url+'-unknown')
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_startup_explains_every_model_status(self):
        statuses = set()
        for spec, key in [(None, 'set'), (object(), ''), (object(), 'set')]:
            with mock.patch.object(library_filter.importlib.util, 'find_spec', return_value=spec), \
                    mock.patch.dict('os.environ', {'OPENROUTER_API_KEY': key}):
                statuses.add(library_filter.model_status())
        self.assertEqual(statuses, set(STARTUP))

    def test_real_phrase_routing_without_sdk_or_provider(self):
        logged = []
        class Handler(LibraryHandler):
            def log_message(self, format, *args):
                logged.append(format % args)
        cars = [{'game': 'gran-turismo', 'sourceVariant': v} for v in ('day', 'night')]
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(library_filter.importlib.util, 'find_spec', return_value=None):
            (Path(folder)/'public/dealership').mkdir(parents=True)
            (Path(folder)/'public/dealership/cars.json').write_text(json.dumps(cars))
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=folder))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def ask(query):
                    data = json.dumps({'query': query, 'catalog': 'dealership'}).encode()
                    with urlopen(Request(f'http://127.0.0.1:{server.server_port}/api/library-filter', data=data,
                                         headers={'Content-Type': 'application/json'}), timeout=3) as response:
                        return json.load(response)
                output = ask('Gran Turismo night cars')
                self.assertEqual((output['status'], output['decided_by'], output['filters']),
                                 ('ok', 'phrase', {'game': 'gran-turismo', 'variant': 'night'}))
                output = ask('private wording about blue night cars')
                self.assertEqual((output['status'], output['reason'], output['filters']), ('error', 'sdk_unavailable', None))
                self.assertIn('SDK is not installed', output['message'])
                self.assertIn('library filter: ok by phrase', logged)
                self.assertIn('library filter: error by nothing (sdk_unavailable)', logged)
                self.assertNotIn('private', str(logged))
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
