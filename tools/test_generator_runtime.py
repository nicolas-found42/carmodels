"""Exercise worker cancellation/replacement through the real HTTP seam, offline."""
import functools
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen

from generator_runtime import GeneratorRuntime
from serve_library import LibraryHandler
import test_car_generator as fixtures


class Tests(unittest.TestCase):
    def test_cancel_frees_process_slot_then_generate_and_save(self):
        with tempfile.TemporaryDirectory() as folder:
            generator = fixtures.Tests().fixture(folder)
            generator.prepare()
            generator.train(epochs=1, device='cpu')
            class Handler(LibraryHandler):
                def log_message(self, *args):
                    pass
            runtime = GeneratorRuntime(folder, python=Path(__file__).resolve().parents[1] / '.venv-generator/bin/python')
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=folder))
            server.generator = runtime
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f'http://127.0.0.1:{server.server_port}/api/generator/'
            def post(path, body):
                with urlopen(Request(url + path, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})) as r:
                    return json.load(r)
            try:
                first = post('start', {'seed': 35})
                self.assertEqual(post(first['id'] + '/cancel', {})['status'], 'cancelled')
                second = post('start', {'seed': 36})
                for attempt in range(200):
                    with urlopen(url + second['id']) as r:
                        progress = json.load(r)
                    if progress['status'] not in ('running', 'confirmation_required'):
                        break
                    time.sleep(.05)
                self.assertEqual(progress['status'], 'ready', progress)
                with urlopen(url + second['id'] + '/model') as r:
                    self.assertTrue(r.read().startswith(b'glTF'))
                saved = post(second['id'] + '/save', {'name': 'HTTP Generated model'})
                self.assertEqual(saved['honestyLabel'], 'Generated model')
                self.assertEqual(len(json.loads((generator.dealership / 'catalog.json').read_text())), 5)
            finally:
                runtime.close()
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == '__main__':
    unittest.main()
