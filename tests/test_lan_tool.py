import ast
import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import core_runner as core
import module1
import lan_bridge as web
from install_tool import patch_core, patch_module
from lan_tool.server import ToolServer, Handler

OWNER = 'a' * 64
OTHER = 'b' * 64
INFOS = [{"udid": "usb-A"}, {"udid": "usb-B"}, {"udid": "usb-C"}]


def payload(count=1, **changes):
    result = dict(keyword='云南旅居', expected_author='测试作者', expected_douyin_id='001Ab',
                  content_type='视频', target_device_count=count,
                  comments='第一条\n第二条\n第三条', scheduled_time='0')
    result.update(changes)
    return result


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        core.initialize_project(str(self.root))
        workbook = core.load_workbook(self.root / 'data/task_cases.xlsx')
        workbook.active.delete_rows(2, workbook.active.max_row)
        workbook.save(self.root / 'data/task_cases.xlsx')
        workbook.close()
        config = self.root / 'config/settings.json'
        settings = json.loads(config.read_text())
        settings.update(cooldown_min_seconds=0, cooldown_max_seconds=0, file_retry_count=1)
        config.write_text(json.dumps(settings))
        self.module_root = patch.object(module1, 'PROJECT_ROOT', str(self.root))
        self.module_root.start()

    def tearDown(self):
        self.module_root.stop()
        self.tmp.cleanup()

    def prepare(self):
        return module1.prepare_devices(INFOS)

    def read(self, binding):
        return module1.read_task(binding['sender_account_id'], physical_device_id=binding['device_id'])

    def finish(self, binding, status='NOT_FOUND', partial=False):
        task = self.read(binding)
        gateway = core.UnifiedGateway(str(self.root), binding['sender_account_id'])
        actions = []
        if status == 'SUCCESS' or partial:
            plan = gateway.generate_strategy(seed=17, task_id=task['task_id'], run_token=task['run_token'])
            actions = [dict(action=v, status='PASSED', message='') for v in plan['execution_order']]
            if partial:
                actions = actions[:1]
            gateway.save_action_results(task['task_id'], task['run_token'], actions)
        gateway.record_result(task['task_id'], status, actions,
                              error_code='EXECUTION_ERROR' if status == 'FAILED' else '',
                              log_message='连接已断开' if status == 'FAILED' else '', run_token=task['run_token'])
        return task

    def expect(self, code, callback):
        with self.assertRaises(core.EngineError) as raised:
            callback()
        self.assertEqual(raised.exception.code, code)


class IntakeTests(Fixture):
    def test_submit_stages_until_actual_roster_and_defaults(self):
        identity = web.submit(self.root, OWNER, '192.168.11.2', payload())
        with core.UnifiedGateway(str(self.root))._session(recover=False) as state:
            self.assertNotIn(identity, state['project_accounts'])
        workbook = core.load_workbook(self.root / 'data/task_cases.xlsx')
        self.assertEqual(workbook.active.max_row, 1)
        workbook.close()
        devices = self.prepare()
        self.assertEqual(len(devices), 1)
        task = self.read(devices[0])
        self.assertEqual(task['task_id'], identity)
        self.assertEqual(task['expected_douyin_id'], '001Ab')

    def test_runtime_submission_waits_for_whole_item(self):
        first = web.submit(self.root, OWNER, 'ip', payload(2))
        devices = module1.prepare_devices(INFOS[:2])
        first_task = self.read(devices[0])
        second = web.submit(self.root, OWNER, 'ip', payload(2, keyword='新任务'))
        core.UnifiedGateway(str(self.root), devices[0]['sender_account_id']).record_result(first_task['task_id'], 'NOT_FOUND', [], run_token=first_task['run_token'])
        self.assertFalse(next(v for v in web.records(self.root, OWNER, False)['records'] if v['task_id']==second)['admitted'])
        # Between the first and second phone is not a whole-item boundary.
        task = self.finish(devices[1])
        self.assertEqual(task['task_id'], first)
        task = self.read(devices[0])
        progress = web.gateway_for(self.root).get_project_progress(second)
        self.assertEqual(progress['target_device_count'], 2)
        if task is None:
            binding = dict(sender_account_id=progress['accounts'][0]['sender_account_id'], device_id=progress['accounts'][0]['physical_device_id'])
            task = self.read(binding)
        self.assertEqual(task['task_id'], second)

    def test_current_active_task_blocks_intake_and_no_replay(self):
        web.submit(self.root, OWNER, 'ip', payload())
        devices = self.prepare()
        task = self.read(devices[0])
        second = web.submit(self.root, OWNER, 'ip', payload())
        with self.assertRaises(RuntimeError):
            self.read(devices[0])
        with web.Store(self.root) as store:
            self.assertFalse(store.row(second)['admitted'])

    def test_capacity_error_preserves_submission_without_invalid_excel_row(self):
        identity = web.submit(self.root, OWNER, 'ip', payload(4, comments='a\nb\nc\nd'))
        self.assertEqual(self.prepare(), [])
        data = web.records(self.root, OWNER, False)['records'][0]
        self.assertFalse(data['admitted'])
        self.assertIn('连接数量', data['intake_error'])
        workbook = core.load_workbook(self.root / 'data/task_cases.xlsx')
        self.assertEqual(workbook.active.max_row, 1)
        workbook.close()

    def test_comment_uniqueness_validation_and_schedule(self):
        self.expect('COMMENTS_INSUFFICIENT', lambda: web.submit(self.root, OWNER, 'ip', payload(2, comments='同一条\n同一条')))
        self.expect('INVALID_SCHEDULE', lambda: web.submit(self.root, OWNER, 'ip', payload(scheduled_time='')))
        self.expect('INVALID_INPUT', lambda: web.submit(self.root, OWNER, 'ip', dict(payload(), owner=OTHER)))

    def test_formula_input_is_literal_text(self):
        web.submit(self.root, OWNER, 'ip', payload(keyword='=HYPERLINK("x")'))
        self.prepare()
        workbook = core.load_workbook(self.root / 'data/task_cases.xlsx')
        self.assertEqual(workbook.active.cell(2,2).data_type, 's')
        workbook.close()

    def test_admit_is_idempotent_after_table_written_before_allocation(self):
        identity = web.submit(self.root, OWNER, 'ip', payload())
        gateway = web.gateway_for(self.root)
        with patch.object(core.UnifiedGateway, '_allocate_task_locked', side_effect=RuntimeError('interrupted')):
            with self.assertRaises(core.EngineError):
                self.prepare()
        self.prepare()
        progress = gateway.get_project_progress(identity)
        assignment = progress['assignment_id']
        self.prepare()
        self.assertEqual(gateway.get_project_progress(identity)['assignment_id'], assignment)
        workbook = core.load_workbook(self.root / 'data/task_cases.xlsx')
        self.assertEqual(workbook.active.max_row, 2)
        workbook.close()

    def test_tool_preserves_worker_list_and_stages_until_roster_refresh(self):
        identity = web.submit(self.root, OWNER, 'ip', payload())
        devices = self.prepare()
        self.assertEqual(len(devices), 1)
        selected = web.gateway_for(self.root).get_project_progress(identity)['accounts'][0]['sender_account_id']
        binding = next(v for v in devices if v['sender_account_id'] == selected)
        self.finish(binding)
        second = web.submit(self.root, OWNER, 'ip', payload(3, keyword='下一条'))
        self.assertIsNone(self.read(binding))
        self.assertFalse(next(v for v in web.records(self.root, OWNER, False)['records'] if v['task_id']==second)['admitted'])
        devices = self.prepare()
        self.assertEqual(len(devices), 3)
        for binding in devices:
            task = self.finish(binding)
            self.assertEqual(task['task_id'], second)

    def test_locked_excel_preserves_queue_then_accepts_after_release(self):
        identity = web.submit(self.root, OWNER, 'ip', payload())
        owner_file = self.root / 'data/~$task_cases.xlsx'
        owner_file.touch()
        gateway = web.gateway_for(self.root)
        roster = [dict(device_id='usb-A', sender_account_id='设备_usb-A')]
        web.prepare(gateway, roster)
        with web.Store(self.root) as store:
            self.assertFalse(store.row(identity)['admitted'])
        owner_file.unlink()
        web.prepare(gateway, roster)
        self.assertTrue(web.records(self.root, OWNER, False)['records'][0]['admitted'])


class CleanupTests(Fixture):
    def failed(self):
        identity = web.submit(self.root, OWNER, 'ip', payload())
        devices = self.prepare()
        self.finish(devices[0], 'FAILED', partial=True)
        return identity, devices

    def test_foreign_cannot_read_error_or_clean(self):
        identity, _ = self.failed()
        self.assertEqual(web.records(self.root, OTHER, False)['records'], [])
        self.assertEqual(web.errors(self.root, OTHER, False)['errors'], [])
        self.expect('NOT_FOUND', lambda: web.cleanup(self.root, identity, OTHER, False))

    def test_cleanup_keeps_history_errors_and_other_state(self):
        identity, devices = self.failed()
        other = web.submit(self.root, OTHER, 'ip', payload(keyword='别人的任务'))
        self.prepare()
        state_before = json.loads((self.root / 'data/runtime_state.json').read_text())
        web.cleanup(self.root, identity, OWNER, False)
        state_after = json.loads((self.root / 'data/runtime_state.json').read_text())
        self.assertNotIn(identity, state_after['project_accounts'])
        self.assertEqual(state_before['project_accounts'][other], state_after['project_accounts'][other])
        record = next(v for v in web.records(self.root, OWNER, False)['records'] if v['task_id']==identity)
        self.assertEqual(sum(record['progress']['counts'].values()), 1)
        self.assertFalse(record['can_cleanup'])
        self.assertEqual(web.errors(self.root, OWNER, False)['errors'][0]['log_message'], '连接已断开')

    def test_normal_not_found_and_mixed_completion_are_not_errors(self):
        identity = web.submit(self.root, OWNER, 'ip', payload(2))
        devices = self.prepare()
        self.finish(devices[0], 'SUCCESS')
        self.finish(devices[1], 'NOT_FOUND')
        self.assertEqual(web.gateway_for(self.root).get_project_progress(identity)['status'], 'FAILED')
        self.assertEqual(web.errors(self.root, OWNER, False)['errors'], [])
        self.expect('NOT_AN_ERROR', lambda: web.cleanup(self.root, identity, OWNER, False))

    def test_running_task_requires_admin_stop_and_live_process_check(self):
        identity = web.submit(self.root, OWNER, 'ip', payload())
        self.read(self.prepare()[0])
        self.expect('STOP_REQUIRED', lambda: web.cleanup(self.root, identity, OWNER, False, True))
        self.expect('STOP_REQUIRED', lambda: web.cleanup(self.root, identity, OWNER, True))
        self.expect('EXECUTION_STILL_RUNNING', lambda: web.cleanup(self.root, identity, OWNER, True, True))
        with patch.object(web, 'stopped_check'):
            web.cleanup(self.root, identity, OWNER, True, True)
        state = json.loads((self.root / 'data/runtime_state.json').read_text())
        self.assertTrue(all(v['active_task'] is None for v in state['devices'].values()))
        archived = web.records(self.root, OWNER, False)['records'][0]['progress']
        self.assertTrue(archived['completed'])
        self.assertEqual(archived['accounts'][0]['error_code'], 'RUN_ENDED_BY_OPERATOR')

    def test_failed_excel_write_leaves_recoverable_targeted_journal(self):
        identity, _ = self.failed()
        with patch.object(web, 'save_book', side_effect=OSError('locked')):
            with self.assertRaises(core.EngineError):
                web.cleanup(self.root, identity, OWNER, False)
        state = json.loads((self.root / 'data/runtime_state.json').read_text())
        self.assertEqual(state['web_cleanup_transaction']['task_id'], identity)
        with web.gateway_for(self.root)._session() as state:
            self.assertNotIn(identity, state['project_accounts'])
            self.assertNotIn('web_cleanup_transaction', state)

    def test_cleanup_after_excel_deleted_before_state_write(self):
        identity, _ = self.failed()
        gateway = web.gateway_for(self.root)
        original = core.UnifiedGateway._save_state
        def fail_after_delete(g, state):
            if 'web_cleanup_transaction' not in state:
                raise OSError('crash after deleting Excel row')
            return original(g, state)
        with patch.object(core.UnifiedGateway, '_save_state', fail_after_delete):
            with self.assertRaises(core.EngineError):
                web.cleanup(self.root, identity, OWNER, False)
        with gateway._session() as state:
            self.assertNotIn(identity, state['project_accounts'])
        self.assertTrue(web.records(self.root, OWNER, False)['records'][0]['progress']['completed'])

    def test_invalid_status_can_be_removed_without_changing_other_rows(self):
        identity, _ = self.failed()
        workbook = core.load_workbook(self.root / 'data/task_cases.xlsx')
        workbook.active.cell(2,5,'PENDDING')
        workbook.save(self.root / 'data/task_cases.xlsx')
        workbook.close()
        with patch.object(web, 'stopped_check'):
            web.cleanup(self.root, identity, OWNER, True, True)
        self.assertNotIn(identity, json.loads((self.root / 'data/runtime_state.json').read_text())['project_accounts'])

    def test_history_and_errors_remain_readable_when_runtime_is_corrupt(self):
        identity, _ = self.failed()
        (self.root / 'data/runtime_state.json').write_text('{bad-json')
        data = web.records(self.root, OWNER, False)
        self.assertTrue(data['warning'])
        self.assertEqual(data['records'][0]['task_id'], identity)
        self.assertFalse(data['records'][0]['can_cleanup'])
        self.assertEqual(web.errors(self.root, OWNER, False)['errors'][0]['log_message'], '连接已断开')


class HttpTests(Fixture):
    def setUp(self):
        super().setUp()
        shutil.copy2(Path(core.__file__), self.root / 'core_runner.py')
        self.server = ToolServer(('127.0.0.1',0),self.root,lan_ip='127.0.0.2')
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        super().tearDown()

    def call(self,path,method='GET',body=None,cookie='',csrf='',host='127.0.0.2',**headers):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        headers.update(Host=host+':'+str(self.server.server_port))
        if cookie:headers['Cookie']=cookie
        if csrf:headers['X-Tool-CSRF']=csrf
        if body is not None:headers['Content-Type']='application/json'
        conn.request(method,path,json.dumps(body) if body is not None else None,headers)
        response=conn.getresponse();data=response.read();status=response.status;new_cookie=response.getheader('Set-Cookie','').split(';')[0];conn.close()
        return status,json.loads(data),new_cookie

    def test_two_browsers_scope_and_csrf_and_reload(self):
        _,a,ca=self.call('/api/context');_,b,cb=self.call('/api/context')
        self.assertFalse(a['data']['admin'])
        status,result,_=self.call('/api/tasks','POST',payload(),ca,a['data']['csrf'])
        self.assertEqual(status,201);identity=result['data']['task_id']
        self.assertEqual(len(self.call('/api/tasks',cookie=ca)[1]['data']['records']),1)
        self.assertEqual(self.call('/api/tasks',cookie=cb)[1]['data']['records'],[])
        self.assertEqual(self.call('/api/task/'+identity,cookie=cb)[0],404)
        self.assertEqual(self.call('/api/cleanup/'+identity,'POST',{},cb,b['data']['csrf'])[0],404)
        self.assertEqual(self.call('/api/tasks','POST',payload(),ca)[0],403)

    def test_local_admin_and_forged_role_cookie_origin_host(self):
        self.assertTrue(self.call('/api/context',host='127.0.0.1')[1]['data']['admin'])
        self.assertEqual(self.call('/api/tasks',host='evil.test')[0],403)
        self.assertEqual(self.call('/api/tasks',Origin='http://evil.test')[0],403)
        _,a,ca=self.call('/api/context')
        self.call('/api/tasks','POST',payload(),ca,a['data']['csrf'])
        forged='dy_tool_browser='+'0'*64+'.'+'0'*64
        self.assertEqual(self.call('/api/tasks',cookie=forged)[1]['data']['records'],[])
        fake=object.__new__(Handler);fake.client_address=('192.168.11.2',123);fake.headers={'Host':'127.0.0.1:8765','X-Forwarded-For':'127.0.0.1'}
        self.assertFalse(fake._admin())


class PatcherTests(unittest.TestCase):
    def test_patches_preserve_business_ast_and_b_root_and_are_idempotent(self):
        base=Path(__file__).resolve().parents[1]/'baseline'
        if not base.exists():
            self.skipTest('baseline snapshot is local validation input')
        before=(base/'module1.py').read_text().replace('PROJECT_ROOT = r"D:\\备份文件\\项目库\\抖音自动发布工具"','PROJECT_ROOT = str(__import__("pathlib").Path(__file__).resolve().parent.parent)')
        after=patch_module(before)
        self.assertIn('Path(__file__).resolve().parent.parent',after)
        self.assertEqual(patch_module(after),after)
        a={v.name:ast.dump(v,include_attributes=False) for v in ast.parse(before).body if isinstance(v,ast.FunctionDef)}
        b={v.name:ast.dump(v,include_attributes=False) for v in ast.parse(after).body if isinstance(v,ast.FunctionDef)}
        for name in set(a)-{'read_task','prepare_devices'}:self.assertEqual(a[name],b[name],name)
        source=(base/'core_runner.py').read_text();new=patch_core(source);self.assertEqual(patch_core(new),new)
        a=ast.parse(source);b=ast.parse(new)
        classes_a={v.name:v for v in a.body if isinstance(v,ast.ClassDef)};classes_b={v.name:v for v in b.body if isinstance(v,ast.ClassDef)}
        for name in set(classes_a)-{'UnifiedGateway'}:self.assertEqual(ast.dump(classes_a[name]),ast.dump(classes_b[name]),name)


if __name__=='__main__':unittest.main()
