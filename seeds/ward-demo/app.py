import http.server
import json
import os
import sys
import store

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8901
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open(os.path.join(BASE_DIR, 'static', 'index.html'), 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.wfile.write(b"Index file not found.")
        elif self.path == '/api/complaints':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = store.get_complaints()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    server_address = ('', PORT)
    httpd = http.server.HTTPServer(server_address, Handler)
    print(f'Starting server on port {PORT}...')
    httpd.serve_forever()
