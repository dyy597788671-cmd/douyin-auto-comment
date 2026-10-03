import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app import VERSION
from app.adapters.yingdao import YingdaoAdapter
from app.store import InputError


def make_server(store, web_dir, port=8765):
    adapter = YingdaoAdapter()

    class Handler(BaseHTTPRequestHandler):
        def send(self, code, data, mime='application/json; charset=utf-8'):
            body = json.dumps(data, ensure_ascii=False).encode('utf-8') if mime.startswith('application/json') else data
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            port = self.server.server_port
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            if self.headers.get('Host') not in hosts:
                self.send(403, {'error': '仅允许通过本机地址访问'}); return False
            origin = self.headers.get('Origin')
            if origin and origin not in {f'http://{h}' for h in hosts}:
                self.send(403, {'error': '不接受其他网页提交的操作'}); return False
            return True

        def do_GET(self):
            if not self.allowed(): return
            path = urlparse(self.path).path
            if path == '/api/state':
                self.send(200, {**store.snapshot(), 'version': VERSION, 'adapter': adapter.health()})
            elif path == '/api/health':
                self.send(200, {'ok': True, 'version': VERSION, 'adapter': adapter.health()})
            elif path in {'/', '/index.html', '/app.js', '/style.css'}:
                filename = 'index.html' if path == '/' else path[1:]
                mime = {'index.html': 'text/html; charset=utf-8', 'app.js': 'text/javascript; charset=utf-8',
                        'style.css': 'text/css; charset=utf-8'}[filename]
                self.send(200, (web_dir / filename).read_bytes(), mime)
            else:
                self.send(404, {'error': '页面不存在'})

        def do_POST(self):
            if not self.allowed(): return
            try:
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise InputError('请提交 JSON 数据')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536: raise InputError('请求大小无效')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict): raise InputError('请求内容必须是对象')
                parts = urlparse(self.path).path.strip('/').split('/')
                if len(parts) == 2 and parts[0] == 'api' and parts[1] in {'devices','targets','tasks','contents'}:
                    self.send(201, {'record': store.create(parts[1], data)})
                elif len(parts) == 4 and parts[:2] == ['api', 'tasks'] and parts[3] == 'status':
                    self.send(200, {'record': store.transition(int(parts[2]), data.get('status'), data.get('note', ''))})
                else: self.send(404, {'error': '接口不存在'})
            except (InputError, ValueError, UnicodeDecodeError) as exc:
                self.send(400, {'error': str(exc)})
            except Exception:
                self.send(500, {'error': '保存失败，请查看控制台日志'})
                import traceback
                traceback.print_exc()

        def log_message(self, fmt, *args):
            print(f'[{self.log_date_time_string()}] {fmt % args}')

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
