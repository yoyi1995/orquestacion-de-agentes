"""Serve observation endpoints on loopback only."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit

from dashboard.data import snapshot

STATIC = Path(__file__).parent / 'static'


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        host = self.headers.get('Host', '')
        if host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        if path == '/api/snapshot':
            try:
                body = json.dumps(snapshot(), ensure_ascii=False).encode('utf-8')
            except (OSError, ValueError):
                self.send_error(503, 'Evidence unavailable')
                return
            mime = 'application/json; charset=utf-8'
        else:
            assets = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'), '/styles.css': ('styles.css', 'text/css'), '/app.js': ('app.js', 'text/javascript')}
            if path not in assets:
                self.send_error(404)
                return
            name, mime = assets[path]
            body = (STATIC / name).read_bytes()
            mime += '; charset=utf-8'
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8787)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Dashboard: http://localhost:{server.server_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
