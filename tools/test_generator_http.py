"""Drive generator HTTP controls on a real localhost server with an injected engine."""
import functools
from http.server import ThreadingHTTPServer
import json
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from serve_library import LibraryHandler


class Engine:
    def start(self, payload):
        return {'id': 'testjob', 'status': 'running'}

    def progress(self, job):
        return {'id': job, 'status': 'ready', 'events': [], 'preview': '/api/generator/testjob/model'}

    def cancel(self, job):
        return {'id': job, 'status': 'cancelled'}

    def confirm(self, job, accept):
        return {'id': job, 'status': 'running' if accept else 'cancelled'}

    def save(self, job, name):
        return {'code': 'GEN_TEST', 'name': name, 'honestyLabel': 'Generated model'}


class Tests(unittest.TestCase):
    def test_endpoints_and_localhost_guards(self):
        class Handler(LibraryHandler):
            generator = Engine()
            def log_message(self, *args):
                pass
        with tempfile.TemporaryDirectory() as folder:
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=folder))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            def post(path, payload, headers=None):
                data = json.dumps(payload).encode()
                with urlopen(Request(base + path, data=data, headers=headers or {'Content-Type': 'application/json'})) as r:
                    return json.load(r)
            try:
                self.assertEqual(post('/api/generator/start', {'method': 'shape space', 'seed': 35})['id'], 'testjob')
                with urlopen(base + '/api/generator/testjob') as response:
                    self.assertEqual(json.load(response)['status'], 'ready')
                self.assertEqual(post('/api/generator/testjob/confirm', {'accept': False})['status'], 'cancelled')
                self.assertEqual(post('/api/generator/testjob/cancel', {})['status'], 'cancelled')
                self.assertEqual(post('/api/generator/testjob/save', {'name': 'New coupe'})['honestyLabel'], 'Generated model')
                for path, payload, headers, expected in [
                    ('/api/generator/start', {}, {'Content-Type': 'application/json', 'Host': 'attacker.test'}, 403),
                    ('/api/generator/testjob/save', {'name': 'X'}, {'Content-Type': 'application/json', 'Origin': 'https://foreign.test'}, 403),
                    ('/api/generator/start', {'request': 'x' * 2049}, None, 400),
                    ('/api/generator/start', {'method': 'invalid'}, None, 400),
                    ('/api/generator/start', {'seed': True}, None, 400),
                    ('/api/generator/start', {'extra': 1}, None, 400),
                    ('/api/generator/testjob/confirm', {'accept': 'yes'}, None, 400),
                    ('/api/generator/testjob/save', {'name': '../file'}, {'Content-Type': 'text/plain'}, 400),
                ]:
                    with self.assertRaises(HTTPError) as error:
                        post(path, payload, headers)
                    self.assertEqual(error.exception.code, expected)
                    error.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
