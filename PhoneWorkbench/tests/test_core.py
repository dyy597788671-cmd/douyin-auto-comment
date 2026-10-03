import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.instance import InstanceLock
from app.server import make_server
from app.store import InputError, Store


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'workbench.db'
        self.store = Store(self.path)
        self.device = self.store.create('devices', {'serial':'phone-001', 'name':'手机01'})
        self.target = self.store.create('targets', {'name':'目标账号'})

    def tearDown(self):
        self.temp.cleanup()

    def task(self):
        return self.store.create('tasks', {'device_id':self.device['id'], 'target_id':self.target['id'], 'keyword':'关键词'})

    def test_reference_validation(self):
        with self.assertRaises(InputError):
            self.store.create('tasks', {'device_id':999, 'target_id':self.target['id']})
        self.assertEqual(self.store.snapshot()['tasks'], [])

    def test_device_serial_unique(self):
        with self.assertRaises(InputError):
            self.store.create('devices', {'serial':'phone-001','name':'另一台'})
        self.assertEqual(len(self.store.snapshot()['devices']), 1)

    def test_identity_verification_requires_identifier(self):
        with self.assertRaises(InputError):
            self.store.create('targets', {'name':'同名账号','verification':'verified'})
        target = self.store.create('targets', {'name':'已核验','account_id':'example','verification':'verified'})
        self.assertIsNotNone(target['verified_at'])

    def test_concurrent_device_claim(self):
        a, b = self.task(), self.task()
        def start(task):
            try: self.store.transition(task['id'], 'active'); return True
            except InputError: return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(start, [a,b]))
        self.assertEqual(results.count(True), 1)
        active = next(t for t in self.store.snapshot()['tasks'] if t['status']=='active')
        self.store.transition(active['id'], 'paused')
        other = b if active['id']==a['id'] else a
        self.store.transition(other['id'], 'active')
        with self.assertRaises(InputError): self.store.transition(active['id'], 'active')

    def test_terminal_and_failure_reason(self):
        task = self.task()
        with self.assertRaises(InputError): self.store.transition(task['id'], 'completed')
        self.store.transition(task['id'], 'active')
        with self.assertRaises(InputError): self.store.transition(task['id'], 'failed')
        self.store.transition(task['id'], 'failed', '无法确认作者')
        with self.assertRaises(InputError): self.store.transition(task['id'], 'active')

    def test_persistence_and_restart(self):
        task = self.task()
        self.store.transition(task['id'], 'active')
        restarted = Store(self.path)
        restarted.recover()
        snapshot = restarted.snapshot()
        self.assertEqual(snapshot['tasks'][0]['status'], 'paused')
        self.assertEqual(snapshot['devices'][0]['serial'], 'phone-001')
        self.assertTrue(any(l['event']=='restart_paused' for l in snapshot['logs']))

    def test_content_link_and_target_consistency(self):
        task = self.task()
        data = {'target_id':self.target['id'], 'task_id':task['id'], 'title':'核验记录', 'url':'https://example.test/1'}
        self.store.create('contents', data)
        with self.assertRaises(InputError): self.store.create('contents', data)
        other = self.store.create('targets', {'name':'另一个账号'})
        with self.assertRaises(InputError): self.store.create('contents', {**data, 'target_id':other['id'], 'url':''})
        self.assertEqual(len(self.store.snapshot()['contents']), 1)

    def test_process_lock(self):
        path = Path(self.temp.name) / 'instance.lock'
        a, b = InstanceLock(path), InstanceLock(path)
        a.acquire()
        try:
            with self.assertRaises(RuntimeError): b.acquire()
        finally: a.release()
        b.acquire(); b.release()

    def test_http_create_errors_and_cross_origin(self):
        server = make_server(self.store, Path(__file__).resolve().parents[1] / 'web', 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base+'/api/state') as r: state=json.load(r)
            self.assertFalse(state['adapter']['connected'])
            req=Request(base+'/api/tasks', data=json.dumps({'device_id':self.device['id'],'target_id':self.target['id']}).encode(), headers={'Content-Type':'application/json'})
            with urlopen(req) as r: self.assertEqual(r.status,201)
            req=Request(base+'/api/devices', data=b'{}', headers={'Content-Type':'application/json','Origin':'https://other.test'})
            with self.assertRaises(HTTPError) as err: urlopen(req)
            self.assertEqual(err.exception.code,403)
            req=Request(base+'/api/targets', data=b'[]', headers={'Content-Type':'application/json'})
            with self.assertRaises(HTTPError) as err: urlopen(req)
            self.assertEqual(err.exception.code,400)
            with urlopen(base+'/') as r: self.assertIn('手机管理工作台',r.read().decode())
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
