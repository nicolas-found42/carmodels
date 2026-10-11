#!/usr/bin/env python3
"""Serve both local car libraries, with an optional server-side semantic filter API."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlparse

from library_filter import live_interpret

ROOT = Path(__file__).resolve().parents[1] / 'dealership'


class LibraryHandler(SimpleHTTPRequestHandler):
    judgment = staticmethod(live_interpret)
    api_lock = threading.Lock()

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

    def do_POST(self):
        if self.path != '/api/library-filter':
            self.reply(404, {'status': 'error', 'message': 'Unknown endpoint.'})
            return
        allowed_hosts = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed_hosts:
            self.reply(403, {'status': 'error', 'message': 'Use the local library address.'})
            return
        self.connection.settimeout(5)
        origin = self.headers.get('Origin')
        expected = f'http://{self.headers.get("Host", "")}'
        if origin is not None and origin != expected:
            self.reply(403, {'status': 'error', 'message': 'Use the local library page.'})
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
            self.reply(200, {key: receipt.get(key) for key in ('status', 'filters', 'message', 'signals', 'usage', 'latency_seconds')})
        except Exception:
            self.reply(503, {'status': 'error', 'message': 'The model catalog is unavailable.'})
        finally:
            self.api_lock.release()

    def do_GET(self):
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
        print(f'Car library: http://localhost:{args.port}/dealership.html', flush=True)
        server.serve_forever()
