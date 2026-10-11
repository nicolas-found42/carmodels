#!/usr/bin/env python3
"""Exercise the actual local HTTP endpoint without provider requests."""
import functools
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from serve_library import LibraryHandler


class Tests(unittest.TestCase):
    def test_http_controls(self):
        calls = []
        class Handler(LibraryHandler):
            judgment = staticmethod(lambda q, cars: (calls.append((q, cars)) or
                {'status': 'ok', 'filters': {'game': 'gran-turismo', 'variant': 'night'}, 'message': 'Applied', 'raw_response': 'PRIVATE'}))
            def log_message(self, *args):
                pass
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'public').mkdir()
            (root/'public/models.json').write_text(json.dumps({'cars': [{'game': 'gran-turismo'}]}))
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
                for data, headers, status in [
                    (b'{}', None, 400), (b'{bad', None, 400),
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
                self.assertEqual(len(calls), 1)
                with self.assertRaises(HTTPError) as caught:
                    request(b'{}', path=url+'-unknown')
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
