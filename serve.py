import http.server
import socketserver
import os
import json
from urllib.parse import urlparse
from backend.earthquake import simulate_collapse
from backend.rasterisation import rasterize_from_baidu
from backend.pathfinder import handle_solve
from backend.extended_neighbors import handle_solve_extended
from backend.afteshock_solve import dynamic_step_service

# 服务器配置
PORT = 9999
ROOT = os.path.dirname(__file__)
WEB_DIR = os.path.join(ROOT, 'web')
WORKSPACE_ROOT = os.path.dirname(ROOT)
Baidu_AK_Server = "服务器端AK"
Baidu_AK_Client = "客户端AK"

class Handler(http.server.SimpleHTTPRequestHandler):
    # 处理跨域请求
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    # 设置JSON响应头
    def _set_json(self, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
    # 重写路径解析
    def translate_path(self, path):
        if path == '/' or path == '/index.html':
            return os.path.join(WEB_DIR, 'index.html')
        rel = path.lstrip('/')
        p = os.path.join(WEB_DIR, rel)
        if os.path.exists(p):
            return p
        return os.path.join(ROOT, rel)

    # 处理路径求解请求
    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get('Content-Length','0'))
        body = self.rfile.read(length) if length>0 else b''

        # 地图栅格化
        if parsed.path == '/api/rasterize':
            try:
                data = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_json(400)
                self.wfile.write(json.dumps({'ok': False, 'error': 'invalid json'}).encode('utf-8'))
                return

            resp = rasterize_from_baidu(data, Baidu_AK_Server, WORKSPACE_ROOT)
            code = 200 if resp.get('ok') else 500
            self._set_json(code)
            self.wfile.write(json.dumps(resp).encode('utf-8'))
            return

        # 室内坍塌模拟
        if parsed.path == '/api/simulate-collapse':
            try:
                data = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_json(400)
                self.wfile.write(json.dumps({'ok': False, 'error': 'invalid json'}).encode('utf-8'))
                return
            try:
                n = int(data.get('size'))
                n = max(5, min(200, n))
                grid = simulate_collapse(n)
                self._set_json(200)
                self.wfile.write(json.dumps({'ok': True, 'size': n, 'grid': grid}).encode('utf-8'))
            except Exception as e:
                self._set_json(500)
                self.wfile.write(json.dumps({'ok': False, 'error': f'simulate failed: {e}'}).encode('utf-8'))
            return

        # 余震
        if parsed.path == '/api/dynamic-step':
            try:
                data = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_json(400)
                self.wfile.write(json.dumps({'ok': False, 'error': 'invalid json'}).encode('utf-8'))
                return
            try:
                result = dynamic_step_service(data)
                self._set_json(200)
                self.wfile.write(json.dumps({'ok': True, **result}).encode('utf-8'))
            except Exception as e:
                self._set_json(500)
                self.wfile.write(json.dumps({'ok': False, 'error': f'dynamic-step failed: {e}'}).encode('utf-8'))
            return

        # 寻路
        if parsed.path == '/api/solve':
            try:
                data = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_json(400)
                self.wfile.write(json.dumps({'ok': False, 'error': 'invalid json'}).encode('utf-8'))
                return
            res = handle_solve(data)
            self._set_json(200 if res.get('ok') else 400)
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # 扩展邻域搜索
        if parsed.path == '/api/solve-extended':
            try:
                data = json.loads(body.decode('utf-8') or '{}')
            except Exception:
                self._set_json(400)
                self.wfile.write(json.dumps({'ok': False, 'error': 'invalid json'}).encode('utf-8'))
                return
            res = handle_solve_extended(data)
            self._set_json(200 if res.get('ok') else 400)
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not Found')

if __name__ == '__main__':
    os.chdir(ROOT)
    class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    with ThreadingHTTPServer(('', PORT), Handler) as httpd:
        print(f'http://localhost:{PORT}')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nServer stopped.')