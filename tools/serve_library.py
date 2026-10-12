#!/usr/bin/env python3
"""Serve both local car libraries, with an optional server-side semantic filter API."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from urllib.parse import urlparse

from library_filter import live_interpret, model_status
from generator_runtime import GeneratorRuntime, validate_start
from generator_review import record

ROOT = Path(__file__).resolve().parents[1] / 'dealership'
STARTUP = {'available': 'uses the TypeSafe model.',
           'sdk_unavailable': 'needs the TypeSafe SDK (typesafe-sdk), which this Python cannot import.',
           'credentials_missing': 'needs OPENROUTER_API_KEY in the server environment.'}


class LibraryHandler(SimpleHTTPRequestHandler):
    judgment = staticmethod(live_interpret)
    api_lock = threading.Lock()
    generator = None

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def reply(self, status, payload):
        data = json.dumps(payload, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def local_request(self):
        allowed_hosts = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed_hosts:
            self.reply(403, {'status': 'error', 'message': 'Use the local library address.'})
            return False
        self.connection.settimeout(5)
        origin = self.headers.get('Origin')
        expected = f'http://{self.headers.get("Host", "")}'
        if origin is not None and origin != expected:
            self.reply(403, {'status': 'error', 'message': 'Use the local library page.'})
            return False
        return True

    def engine(self):
        if self.generator is not None:
            return self.generator
        return self.server.generator

    def generator_post(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Invalid JSON request')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object')
            if self.path == '/api/generator-review':
                result = record(Path(self.directory) / 'generator', payload)
            elif self.path == '/api/generator/start':
                validate_start(payload)
                result = self.engine().start(payload)
            else:
                match = re.fullmatch(r'/api/generator/([a-zA-Z0-9]{1,64})/(cancel|confirm|save)', self.path)
                if not match:
                    self.reply(404, {'status': 'error', 'message': 'Unknown endpoint.'})
                    return
                job, action = match.groups()
                if action == 'cancel' and payload == {}:
                    result = self.engine().cancel(job)
                elif action == 'confirm' and set(payload) == {'accept'} and type(payload['accept']) is bool:
                    result = self.engine().confirm(job, payload['accept'])
                elif action == 'save' and set(payload) == {'name'} and isinstance(payload['name'], str) and \
                        len(payload['name']) <= 120 and not any(ord(c) < 32 for c in payload['name']):
                    result = self.engine().save(job, payload['name'])
                else:
                    raise ValueError('Invalid generator action')
            self.reply(200, result)
            self.log_message('generator outcome: %s', result.get('status', 'saved'))
        except BlockingIOError:
            self.reply(429, {'status': 'error', 'message': 'A generation job is already running.'})
        except KeyError:
            self.reply(404, {'status': 'error', 'message': 'Unknown generation job.'})
        except (ValueError, UnicodeError, OSError):
            self.reply(400, {'status': 'error', 'message': 'Invalid generator request or model already saved.'})
        except Exception:
            self.reply(503, {'status': 'error', 'message': 'Generator environment unavailable.'})

    def do_POST(self):
        if self.path not in ('/api/library-filter', '/api/generator-review') and not self.path.startswith('/api/generator/'):
            self.reply(404, {'status': 'error', 'message': 'Unknown endpoint.'})
            return
        if not self.local_request():
            return
        if self.path.startswith('/api/generator/') or self.path == '/api/generator-review':
            self.generator_post()
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Invalid request')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or set(payload) not in ({'query'}, {'query', 'catalog'}):
                raise ValueError('Invalid payload')
            catalog = payload.get('catalog', 'source')
            if catalog not in ('source', 'dealership'):
                raise ValueError('Invalid catalog')
            query = payload['query']
            if not isinstance(query, str) or not 1 <= len(query.strip()) <= 500 or any(ord(c) < 32 for c in query):
                raise ValueError('Invalid query')
        except (ValueError, UnicodeError, OSError):
            self.reply(400, {'status': 'error', 'message': 'Enter a query of 1 to 500 printable characters.'})
            return
        if not self.api_lock.acquire(blocking=False):
            self.reply(429, {'status': 'error', 'message': 'A filter request is already running.'})
            return
        try:
            path = 'public/models.json' if catalog == 'source' else 'public/dealership/cars.json'
            data = json.loads((Path(self.directory) / path).read_text())
            cars = data['cars'] if catalog == 'source' else data
            receipt = self.judgment(query, cars, catalog=catalog)
            # Do not expose raw provider envelopes in the UI; local experiments retain those separately.
            self.reply(200, {key: receipt.get(key) for key in ('status', 'filters', 'message', 'decided_by', 'reason',
                                                               'signals', 'usage', 'latency_seconds')})
            # The outcome, never the query text, goes to the server log.
            self.log_message('library filter: %s by %s%s', receipt.get('status'), receipt.get('decided_by') or 'nothing',
                             f" ({receipt['reason']})" if receipt.get('reason') else '')
        except Exception:
            self.reply(503, {'status': 'error', 'message': 'The model catalog is unavailable.'})
        finally:
            self.api_lock.release()

    def do_GET(self):
        if self.path == '/api/generator/current':
            if not self.local_request():
                return
            try:
                self.reply(200, self.engine().latest())
            except Exception:
                self.reply(503, {'message': 'Generator status unavailable.'})
            return
        if self.path in ('/api/generator-review', '/api/generator/config'):
            if not self.local_request():
                return
            try:
                path = Path(self.directory) / 'generator' / ('review-session/presentation.json' if self.path == '/api/generator-review' else 'training.json')
                data = json.loads(path.read_text())
                self.reply(200, data if self.path == '/api/generator-review' else {'novelty_default': data['novelty_default']})
            except Exception:
                self.reply(503, {'message': 'Generator training or review session is unavailable.'})
            return
        match = re.fullmatch(r'/api/generator/([a-zA-Z0-9]{1,64})(/model)?', self.path)
        if match:
            if not self.local_request():
                return
            try:
                job, model = match.groups()
                if model:
                    data = self.engine().model(job)
                    self.send_response(200)
                    self.send_header('Content-Type', 'model/gltf-binary')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.reply(200, self.engine().progress(job))
            except KeyError:
                self.reply(404, {'status': 'error', 'message': 'Unknown generation job.'})
            except Exception:
                self.reply(503, {'status': 'error', 'message': 'Generated model unavailable.'})
            return
        if urlparse(self.path).path == '/':
            self.send_response(302)
            self.send_header('Location', '/dealership.html')
            self.end_headers()
            return
        super().do_GET()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8081)
    args = parser.parse_args()
    with ThreadingHTTPServer(('127.0.0.1', args.port), functools.partial(LibraryHandler, directory=str(ROOT))) as server:
        server.generator = GeneratorRuntime(ROOT)
        print(f'Car library: http://localhost:{args.port}/dealership.html', flush=True)
        print('Natural-language filter: exact game/variant phrases work offline; other wording ' +
              STARTUP[model_status()], flush=True)
        try:
            server.serve_forever()
        finally:
            server.generator.close()
