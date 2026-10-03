import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class InputError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def field(data, name, required=False, limit=500):
    value = data.get(name, '')
    if not isinstance(value, str):
        raise InputError(f'{name} 必须是文本')
    value = value.strip()
    if required and not value:
        raise InputError(f'{name} 不能为空')
    if len(value) > limit:
        raise InputError(f'{name} 最多 {limit} 个字符')
    return value


class Store:
    transitions = {
        'pending': {'active', 'cancelled'},
        'active': {'paused', 'completed', 'failed', 'cancelled'},
        'paused': {'active', 'cancelled'},
        'completed': set(), 'failed': set(), 'cancelled': set(),
    }

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as c:
            c.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS devices(
                    id INTEGER PRIMARY KEY, serial TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL, model TEXT NOT NULL, login_account TEXT NOT NULL,
                    note TEXT NOT NULL, connection_state TEXT NOT NULL DEFAULT 'unknown',
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS targets(
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, account_id TEXT NOT NULL,
                    profile_url TEXT NOT NULL, avatar_ref TEXT NOT NULL, group_name TEXT NOT NULL,
                    note TEXT NOT NULL, verification TEXT NOT NULL, verified_at TEXT,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(
                    id INTEGER PRIMARY KEY, device_id INTEGER NOT NULL REFERENCES devices(id),
                    target_id INTEGER NOT NULL REFERENCES targets(id), keyword TEXT NOT NULL,
                    content_type TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'content_review',
                    status TEXT NOT NULL DEFAULT 'pending', note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS contents(
                    id INTEGER PRIMARY KEY, target_id INTEGER NOT NULL REFERENCES targets(id),
                    task_id INTEGER REFERENCES tasks(id), title TEXT NOT NULL, url TEXT NOT NULL,
                    published_at TEXT NOT NULL, author_account TEXT NOT NULL,
                    identity_result TEXT NOT NULL, screenshot_ref TEXT NOT NULL,
                    note TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE UNIQUE INDEX IF NOT EXISTS unique_content_link
                    ON contents(url) WHERE url <> '';
                CREATE TABLE IF NOT EXISTS logs(
                    id INTEGER PRIMARY KEY, entity TEXT NOT NULL, entity_id INTEGER NOT NULL,
                    event TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
                PRAGMA user_version=1;
            ''')

    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    @staticmethod
    def log(c, entity, entity_id, event, detail):
        c.execute('INSERT INTO logs(entity,entity_id,event,detail,created_at) VALUES(?,?,?,?,?)',
                  (entity, entity_id, event, detail, now()))

    @staticmethod
    def exists(c, table, value):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise InputError('关联编号必须为正整数')
        if not c.execute(f'SELECT id FROM {table} WHERE id=?', (value,)).fetchone():
            raise InputError('所选设备、账号或任务不存在')

    def snapshot(self):
        with self.connection() as c:
            return {name: [dict(r) for r in c.execute(
                f'SELECT * FROM {name} ORDER BY id DESC' + (' LIMIT 500' if name == 'logs' else ''))]
                for name in ('devices', 'targets', 'tasks', 'contents', 'logs')}

    def create(self, entity, data):
        if not isinstance(data, dict):
            raise InputError('请求内容必须是对象')
        with self.connection() as c:
            timestamp = now()
            if entity == 'devices':
                keys = ['serial', 'name', 'model', 'login_account', 'note']
                values = [field(data, k, k in {'serial', 'name'}) for k in keys]
            elif entity == 'targets':
                keys = ['name', 'account_id', 'profile_url', 'avatar_ref', 'group_name', 'note', 'verification']
                verification = data.get('verification', 'pending')
                if verification not in {'pending', 'verified'}:
                    raise InputError('账号确认状态无效')
                if verification == 'verified' and not (field(data, 'account_id') or field(data, 'profile_url')):
                    raise InputError('确认身份前请填写抖音号或主页链接')
                data = {**data, 'verification': verification}
                values = [field(data, k, k == 'name') for k in keys]
                keys.append('verified_at')
                values.append(timestamp if verification == 'verified' else None)
            elif entity == 'tasks':
                self.exists(c, 'devices', data.get('device_id'))
                self.exists(c, 'targets', data.get('target_id'))
                content_type = data.get('content_type', 'all')
                if content_type not in {'all', 'video', 'image'}:
                    raise InputError('内容类型无效')
                keys = ['device_id', 'target_id', 'keyword', 'content_type', 'updated_at']
                values = [data['device_id'], data['target_id'], field(data, 'keyword'), content_type, timestamp]
            elif entity == 'contents':
                self.exists(c, 'targets', data.get('target_id'))
                task_id = data.get('task_id') or None
                if task_id is not None:
                    self.exists(c, 'tasks', task_id)
                    task = c.execute('SELECT target_id FROM tasks WHERE id=?', (task_id,)).fetchone()
                    if task['target_id'] != data['target_id']:
                        raise InputError('作品目标账号与任务目标账号不一致')
                result = data.get('identity_result', 'pending')
                if result not in {'pending', 'matched', 'mismatched', 'not_found'}:
                    raise InputError('核验结果无效')
                keys = ['target_id', 'task_id', 'title', 'url', 'published_at', 'author_account',
                        'identity_result', 'screenshot_ref', 'note']
                values = [data['target_id'], task_id, field(data, 'title', True), field(data, 'url', limit=2000),
                          field(data, 'published_at'), field(data, 'author_account'), result,
                          field(data, 'screenshot_ref', limit=2000), field(data, 'note')]
            else:
                raise InputError('未知数据类型')
            keys.append('created_at'); values.append(timestamp)
            try:
                row_id = c.execute(f"INSERT INTO {entity}({','.join(keys)}) VALUES({','.join('?' for _ in keys)})", values).lastrowid
            except sqlite3.IntegrityError as exc:
                raise InputError('设备标识或作品链接重复，记录未保存') from exc
            self.log(c, entity, row_id, 'created', '新建记录')
            return dict(c.execute(f'SELECT * FROM {entity} WHERE id=?', (row_id,)).fetchone())

    def transition(self, task_id, status, note=''):
        if not isinstance(status, str) or status not in self.transitions:
            raise InputError('任务状态无效')
        note = field({'note': note}, 'note')
        with self.connection() as c:
            c.execute('BEGIN IMMEDIATE')
            self.exists(c, 'tasks', task_id)
            task = c.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
            if status not in self.transitions[task['status']]:
                raise InputError('当前状态不允许此操作')
            if status == 'active' and c.execute(
                "SELECT id FROM tasks WHERE device_id=? AND status='active' AND id<>?",
                (task['device_id'], task_id)).fetchone():
                raise InputError('该设备已有进行中的任务，请先暂停或结束')
            if status == 'failed' and not note:
                raise InputError('请填写失败原因')
            c.execute('UPDATE tasks SET status=?,note=?,updated_at=? WHERE id=?', (status, note, now(), task_id))
            self.log(c, 'tasks', task_id, status, note or f"{task['status']} → {status}")
            return dict(c.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone())

    def recover(self):
        with self.connection() as c:
            for row in c.execute("SELECT id FROM tasks WHERE status='active'").fetchall():
                c.execute("UPDATE tasks SET status='paused',note=?,updated_at=? WHERE id=?",
                          ('程序重启，等待人工确认后恢复', now(), row['id']))
                self.log(c, 'tasks', row['id'], 'restart_paused', '程序重启后暂停，保留记录')
