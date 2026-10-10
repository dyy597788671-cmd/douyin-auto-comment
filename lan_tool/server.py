"""One local HTTP service for B's ShadowBot project. Python stdlib only."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import sys
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python_deps"))
import core_runner as core
import lan_bridge as bridge

ASSETS = Path(__file__).resolve().parent
COOKIE = "dy_tool_browser"


class ToolServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, root, lan_ip="192.168.11.10"):
        self.root = Path(root).resolve()
        self.lan_ip = lan_ip
        for path in (self.root / "core_runner.py", self.root / "data" / "task_cases.xlsx"):
            if not path.is_file():
                raise RuntimeError("项目目录不正确，缺少：" + str(path))
        with bridge.Store(root) as store:
            self.secret = bytes.fromhex(store.meta("secret"))
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "DouyinTool/" + bridge.VERSION

    def log_message(self, fmt, *args):
        return

    def _valid_host(self):
        expected = {"127.0.0.1", "localhost", self.server.lan_ip}
        parsed = urlsplit("http://" + self.headers.get("Host", ""))
        try:
            return parsed.hostname in expected and parsed.port == self.server.server_port and not parsed.username
        except ValueError:
            return False

    def _admin(self):
        # Ignore forwarded IPs and user-supplied role/account fields.
        host = urlsplit("http://" + self.headers.get("Host", "")).hostname
        return ipaddress.ip_address(self.client_address[0]).is_loopback and host in ("127.0.0.1", "localhost")

    def _signature(self, text):
        return hmac.new(self.server.secret, text.encode(), hashlib.sha256).hexdigest()

    def _identity(self):
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            value = cookies[COOKIE].value if COOKIE in cookies else ""
            owner, signature = value.rsplit(".", 1)
            if len(owner) != 64 or not all(c in "0123456789abcdef" for c in owner) or not hmac.compare_digest(signature, self._signature(owner)):
                raise ValueError()
            return owner, None
        except (ValueError, KeyError):
            owner = secrets.token_hex(32)
            value = owner + "." + self._signature(owner)
            return owner, COOKIE + "=" + value + "; Path=/; HttpOnly; SameSite=Strict; Max-Age=157680000"

    def _headers(self, status, mime, length, cookie=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _json(self, value, status=200, cookie=None):
        data = core._json(value).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(data), cookie)
        self.wfile.write(data)

    def _guard(self):
        if not self._valid_host():
            raise core.EngineError("ACCESS_DENIED", "访问地址不正确")
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + self.headers.get("Host"):
            raise core.EngineError("ACCESS_DENIED", "跨站请求已拒绝")
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            raise core.EngineError("ACCESS_DENIED", "跨站请求已拒绝")

    def _error(self, exc, cookie):
        code = getattr(exc, "code", "TOOL_ERROR")
        status = 404 if code == "NOT_FOUND" else 403 if code == "ACCESS_DENIED" else 409 if code in ("STOP_REQUIRED", "EXECUTION_STILL_RUNNING", "NOT_AN_ERROR", "LOCK_TIMEOUT", "EXCEL_IO_FAILED", "CLEANUP_PENDING") else 400
        message = str(exc) if self._admin() or code in ("INVALID_INPUT", "COMMENTS_INSUFFICIENT", "INVALID_CONTENT_TYPE", "INVALID_TARGET_COUNT", "INVALID_SCHEDULE", "NOT_FOUND", "ACCESS_DENIED", "STOP_REQUIRED", "NOT_AN_ERROR") else "当前操作未完成，请联系B电脑处理；你的提交和历史仍保留"
        self._json({"ok": False, "error_code": code, "message": message}, status, cookie)

    def do_GET(self):
        cookie = None
        try:
            self._guard()
            owner, cookie = self._identity()
            route = urlsplit(self.path).path
            admin = self._admin()
            if route == "/api/context":
                self._json({"ok": True, "data": {"application": "douyin-local-tool", "admin": admin, "csrf": self._signature("csrf:" + owner),
                            "lan_url": "http://" + self.server.lan_ip + ":" + str(self.server.server_port),
                            "version": bridge.VERSION}}, cookie=cookie)
            elif route == "/api/tasks":
                self._json({"ok": True, "data": bridge.records(self.server.root, owner, admin)}, cookie=cookie)
            elif route.startswith("/api/task/"):
                identity = unquote(route[len("/api/task/"):])
                records = bridge.records(self.server.root, owner, admin)["records"]
                record = next((v for v in records if v["task_id"] == identity), None)
                if record is None:
                    raise core.EngineError("NOT_FOUND", "找不到这个任务")
                self._json({"ok": True, "data": record}, cookie=cookie)
            elif route == "/api/errors":
                self._json({"ok": True, "data": bridge.errors(self.server.root, owner, admin)}, cookie=cookie)
            elif route in ("/", "/app.js", "/style.css"):
                name = "index.html" if route == "/" else route[1:]
                mime = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[name]
                data = (ASSETS / name).read_bytes()
                self._headers(200, mime + "; charset=utf-8", len(data), cookie)
                self.wfile.write(data)
            else:
                raise core.EngineError("NOT_FOUND", "找不到这个页面")
        except Exception as exc:
            self._error(exc, cookie)

    def do_POST(self):
        cookie = None
        try:
            self._guard()
            owner, cookie = self._identity()
            token = self.headers.get("X-Tool-CSRF", "")
            if not hmac.compare_digest(token, self._signature("csrf:" + owner)):
                raise core.EngineError("ACCESS_DENIED", "页面身份已变化，请重新打开页面")
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 262144 or self.headers.get_content_type() != "application/json":
                raise core.EngineError("INVALID_INPUT", "请求格式不正确或内容过长")
            values = json.loads(self.rfile.read(length))
            route = urlsplit(self.path).path
            if route == "/api/tasks":
                identity = bridge.submit(self.server.root, owner, self.client_address[0], values)
                self._json({"ok": True, "data": {"task_id": identity, "message": "提交已保存，将在影刀条目边界接入执行"}}, 201, cookie)
            elif route.startswith("/api/cleanup/"):
                if not isinstance(values, dict) or set(values) - {"stopped"} or not isinstance(values.get("stopped", False), bool):
                    raise core.EngineError("INVALID_INPUT", "清理参数不正确")
                identity = unquote(route[len("/api/cleanup/"):])
                result = bridge.cleanup(self.server.root, identity, owner, self._admin(), values.get("stopped", False))
                self._json({"ok": True, "data": result}, cookie=cookie)
            else:
                raise core.EngineError("NOT_FOUND", "找不到这个操作")
        except Exception as exc:
            self._error(exc, cookie)


def main():
    parser = argparse.ArgumentParser(description="抖音任务工具")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--lan-ip", default="192.168.11.10")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    server = ToolServer(("0.0.0.0", args.port), args.root, args.lan_ip)
    print("抖音任务工具 v" + bridge.VERSION, flush=True)
    print("B本机管理：http://127.0.0.1:" + str(server.server_port), flush=True)
    print("其他电脑访问：http://" + args.lan_ip + ":" + str(server.server_port), flush=True)
    print("保持此窗口开启，关闭窗口会停止网页服务。", flush=True)
    if args.open:
        webbrowser.open("http://127.0.0.1:" + str(server.server_port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
