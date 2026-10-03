import argparse
import threading
import webbrowser
from pathlib import Path

from app.server import make_server
from app.store import Store
from app.instance import InstanceLock


def main():
    parser = argparse.ArgumentParser(description='本地手机管理工作台')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    lock = InstanceLock(root / 'data' / 'instance.lock')
    try:
        lock.acquire()
    except RuntimeError as exc:
        print(exc)
        return 1
    store = Store(root / 'data' / 'workbench.db')
    try:
        server = make_server(store, root / 'web', args.port)
    except OSError:
        print('启动失败：端口可能被占用，请关闭已有工作台或使用 --port 8766。')
        lock.release()
        return 1
    store.recover()
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'手机管理工作台 v0.1.0\n访问地址：{url}\n数据目录：{root / "data"}\n退出：Ctrl+C')
    if not args.no_browser:
        threading.Timer(.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n工作台已停止，数据已保留。')
    finally:
        server.server_close()
        lock.release()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
