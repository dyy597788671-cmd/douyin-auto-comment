"""Local web intake and cleanup. Mobile control remains in ShadowBot.

The existing project lock protects Excel, runtime state and this one SQLite
record file. Only ShadowBot's calls supply the actual connected-device roster.
"""
from __future__ import annotations

import copy
import ctypes
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import subprocess
import time
from pathlib import Path

import core_runner as core

VERSION = "1.0.0"
DB_NAME = "lan_tool.sqlite3"


class Store:
    def __init__(self, root):
        self.path = Path(root) / "data" / DB_NAME
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS records (
                task_id TEXT PRIMARY KEY, owner TEXT, payload TEXT NOT NULL,
                submitted_at TEXT NOT NULL, source_ip TEXT NOT NULL DEFAULT '',
                admitted INTEGER NOT NULL DEFAULT 0,
                retained_only INTEGER NOT NULL DEFAULT 0,
                progress TEXT, intake_error TEXT NOT NULL DEFAULT '');
        """)
        self.db.execute("INSERT OR IGNORE INTO meta VALUES ('secret', ?)",
                        (json.dumps(secrets.token_hex(32)),))
        self.db.commit()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    def meta(self, key, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, core._json(value)))
        self.db.commit()

    def row(self, identity):
        row = self.db.execute("SELECT * FROM records WHERE task_id=?", (identity,)).fetchone()
        return dict(row) if row else None

    def rows(self, owner=None, admin=False):
        sql, params = "SELECT * FROM records", ()
        if not admin:
            sql, params = sql + " WHERE owner=?", (owner,)
        return [dict(row) for row in self.db.execute(sql + " ORDER BY submitted_at DESC,task_id DESC", params)]


def gateway_for(root):
    settings = Path(root) / "config" / "settings.json"
    configured = json.loads(settings.read_text(encoding="utf-8-sig")).get("sender_accounts", []) if settings.exists() else []
    return core.UnifiedGateway(str(root), configured[0] if configured else "web-tool")


def validate_payload(values, gateway):
    allowed = {"keyword", "expected_author", "expected_douyin_id", "content_type",
               "comments", "target_device_count", "scheduled_time"}
    if not isinstance(values, dict) or set(values) - allowed:
        raise core.EngineError("INVALID_INPUT", "任务字段格式不正确")
    result = {}
    for name, title, limit in (("keyword", "关键词", 512),
                               ("expected_author", "作者昵称", 256),
                               ("expected_douyin_id", "抖音号", 256),
                               ("content_type", "作品类型", 8)):
        raw = values.get(name)
        if not isinstance(raw, str) or not raw.strip() or len(raw) > limit:
            raise core.EngineError("INVALID_INPUT", title + "不能为空或超过长度限制")
        result[name] = raw.strip()
    result["expected_douyin_id"] = core._douyin_id(result["expected_douyin_id"])
    if not result["expected_douyin_id"] or re.search(r"\s|[:：]", result["expected_douyin_id"]):
        raise core.EngineError("INVALID_INPUT", "请输入完整抖音号")
    core._validate_route(result["content_type"], result["content_type"], {})
    comments = values.get("comments")
    if not isinstance(comments, str) or len(comments) > 32767:
        raise core.EngineError("INVALID_INPUT", "评论必须为不超过32767字的文本，每行一条")
    pool = core._comment_pool(comments)
    count = core._target_count(values.get("target_device_count"))
    if count is None:
        raise core.EngineError("INVALID_INPUT", "请填写执行设备数量")
    if len(pool) < count:
        raise core.EngineError("COMMENTS_INSUFFICIENT", "去重后的评论数量必须不少于执行设备数量")
    result.update(comments="\n".join(pool), target_device_count=count)
    scheduled = values.get("scheduled_time", "0")
    if isinstance(scheduled, bool) or not isinstance(scheduled, (str, int, float)):
        raise core.EngineError("INVALID_INPUT", "执行时间格式不正确")
    gateway.scheduler.due_at("validation", scheduled, {"relative_schedules": {}}, core._utcnow())
    result["scheduled_time"] = core._text(scheduled)
    return result


def submit(root, owner, source_ip, values):
    gateway = gateway_for(root)
    payload = validate_payload(values, gateway)
    identity = "W" + core._utcnow().astimezone(gateway.scheduler.tz).strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(8)
    # Intake only; this does not write Excel or change an executing allocation.
    with core._project_lock(gateway.lock_path, gateway.settings["lock_timeout_seconds"]):
        with Store(root) as store:
            store.db.execute("INSERT INTO records(task_id,owner,payload,submitted_at,source_ip) VALUES (?,?,?,?,?)",
                             (identity, owner, core._json(payload), core._utcnow().isoformat(), source_ip))
            store.db.commit()
    return identity


def read_book(gateway):
    """Inspect/target-delete an invalid status without discarding other rows."""
    data = gateway.scheduler._retry(gateway.scheduler.path.read_bytes)
    workbook = core.load_workbook(io.BytesIO(data), data_only=False)
    name = gateway.settings["worksheet"]
    sheet = workbook[name] if name else workbook.active
    columns = {}
    for cell in sheet[1]:
        name = core._text(cell.value)
        if name in core.HEADERS + core.OPTIONAL_HEADERS:
            if name in columns:
                workbook.close()
                raise core.EngineError("EXCEL_SCHEMA_INVALID", "任务表字段重复：" + name)
            columns[name] = cell.column
    if set(core.HEADERS + ("Content_Type", "Comments")) - set(columns):
        workbook.close()
        raise core.EngineError("EXCEL_SCHEMA_INVALID", "任务表缺少必需字段")
    rows = {}
    for index in range(2, sheet.max_row + 1):
        cell = sheet.cell(index, columns["Task_ID"])
        if cell.value is None:
            continue
        if cell.data_type == "f":
            workbook.close()
            raise core.EngineError("EXCEL_FORMULA_FORBIDDEN", "任务ID不能为公式")
        identity = core._task_id(cell.value)
        if identity in rows:
            workbook.close()
            raise core.EngineError("DUPLICATE_TASK_ID", "任务ID重复，不能判断应清理哪一行")
        rows[identity] = index
    return workbook, sheet, columns, rows, hashlib.sha256(data).hexdigest()


def save_book(gateway, workbook, digest):
    output = io.BytesIO()
    workbook.save(output)
    def write():
        if hashlib.sha256(gateway.scheduler.path.read_bytes()).hexdigest() != digest:
            raise core.EngineError("EXCEL_WRITE_CONFLICT", "任务表被其他程序修改，未覆盖")
        core._atomic_bytes(gateway.scheduler.path, output.getvalue())
    gateway.scheduler._retry(write)


def table_payload(sheet, columns, row):
    mapping = {"keyword": "Query_Keyword", "expected_author": "Expected_Author",
               "expected_douyin_id": "Expected_Douyin_ID", "content_type": "Content_Type",
               "comments": "Comments", "target_device_count": "Target_Device_Count",
               "scheduled_time": "Scheduled_Time"}
    return {name: core._text(sheet.cell(row, columns[field]).value)
            for name, field in mapping.items() if field in columns}


def capture(gateway, state, table=None):
    """Event-based history, independent of later removal; no polling worker."""
    with Store(gateway.root) as store:
        for identity, project in state["project_accounts"].items():
            progress = gateway._project_progress(state, identity)
            payload = (table or {}).get(identity, {})
            if not payload:
                active = next((v.get("active_task") for v in state["devices"].values()
                               if v.get("active_task", {}) and v["active_task"]["task_id"] == identity), {})
                payload = {k: active.get(k, "") for k in ("keyword", "expected_author", "expected_douyin_id", "content_type", "target_device_count")}
            when = progress.get("allocated_at") or next((v.get("claimed_at") for v in progress["accounts"] if v.get("claimed_at")), core._utcnow().isoformat())
            store.db.execute("INSERT OR IGNORE INTO records(task_id,payload,submitted_at,admitted) VALUES (?,?,?,1)",
                             (identity, core._json(payload), when))
            store.db.execute("UPDATE records SET progress=?,admitted=1 WHERE task_id=?", (core._json(progress), identity))
            if table and identity in table:
                store.db.execute("UPDATE records SET payload=? WHERE task_id=? AND owner IS NULL", (core._json(payload), identity))
        store.db.commit()


def snapshot(gateway, state):
    try:
        if (gateway.root / "data" / DB_NAME).exists():
            capture(gateway, state)
    except Exception as exc:
        gateway.logger.warning("web_history_unavailable reason=%s", exc)


def process_stamp(pid):
    if os.name != "nt":
        try:
            return Path("/proc", str(pid), "stat").read_text().rsplit(")", 1)[1].split()[19]
        except (OSError, IndexError):
            return None
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        # Access denied means live but inaccessible, never treat it as stopped.
        return "unknown-live" if ctypes.get_last_error() == 5 else None
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in times)):
            return "unknown-live"
        return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
    finally:
        kernel.CloseHandle(handle)


def register_runner(store, reset=False):
    runners = [] if reset else store.meta("runners", [])
    runners = [v for v in runners if process_stamp(v["pid"]) == v["stamp"]]
    own = {"pid": os.getpid(), "stamp": process_stamp(os.getpid())}
    if own not in runners:
        runners.append(own)
    store.put_meta("runners", runners)


def safe_boundary(state):
    if any(v.get("active_task") for v in state["devices"].values()):
        return False
    for project in state["project_accounts"].values():
        entries = list(project["accounts"].values())
        if any(v["status"] == "RUNNING" for v in entries):
            return False
        if any(v.get("claimed_at") or v.get("result") for v in entries) and any(v["status"] not in core.TERMINAL_STATUSES for v in entries):
            return False
    return True


def _admit(gateway, state, roster):
    if not safe_boundary(state):
        return
    with Store(gateway.root) as store:
        pending = list(store.db.execute("SELECT * FROM records WHERE admitted=0 AND retained_only=0 ORDER BY submitted_at,task_id"))
        for record in pending:
            identity, payload = record["task_id"], json.loads(record["payload"])
            try:
                eligible = [v for v in roster if state["devices"].get(v["sender_account_id"], {}).get("state") != "BLOCKED"]
                if payload["target_device_count"] > len(eligible):
                    raise core.EngineError("TARGET_COUNT_EXCEEDS_CONNECTED", "执行设备数量超过本次影刀可用连接数量；提交已保留")
                workbook, sheet, columns, rows, digest = read_book(gateway)
                try:
                    if identity not in rows:
                        for field in ("Expected_Douyin_ID", "Target_Device_Count"):
                            if field not in columns:
                                columns[field] = sheet.max_column + 1
                                sheet.cell(1, columns[field], field)
                        row = sheet.max_row + 1
                        if row > 2:
                            for column in range(1, sheet.max_column + 1):
                                sheet.cell(row, column)._style = copy.copy(sheet.cell(2, column)._style)
                        fields = dict(Task_ID=identity, Query_Keyword=payload["keyword"], Expected_Author=payload["expected_author"],
                                      Expected_Douyin_ID=payload["expected_douyin_id"], Content_Type=payload["content_type"],
                                      Comments=payload["comments"], Target_Device_Count=payload["target_device_count"],
                                      Scheduled_Time=payload["scheduled_time"], Status="PENDING", Executed_Actions="", Result_Message="")
                        for field, value in fields.items():
                            cell = sheet.cell(row, columns[field], value)
                            if isinstance(value, str):
                                cell.data_type = "s"
                        save_book(gateway, workbook, digest)
                    else:
                        existing = table_payload(sheet, columns, rows[identity])
                        if any(core._text(existing.get(key)) != core._text(value) for key, value in payload.items()):
                            raise core.EngineError("TASK_WRITE_CONFLICT", "同名任务内容被改变，未覆盖")
                finally:
                    workbook.close()
                gateway._allocate_task_locked(state, identity, roster)
                store.db.execute("UPDATE records SET admitted=1,intake_error='' WHERE task_id=?", (identity,))
            except Exception as exc:
                message = str(exc)
                store.db.execute("UPDATE records SET intake_error=? WHERE task_id=?", (message, identity))
                # A persisted engine transaction must recover before more writes.
                if state.get("pending_transaction"):
                    store.db.commit()
                    return
            store.db.commit()


def prepare(gateway, roster):
    try:
        with gateway._session() as state:
            with Store(gateway.root) as store:
                store.put_meta("roster", core._connected_devices(roster))
                register_runner(store, reset=True)
            workbook, sheet, columns, rows, _ = read_book(gateway)
            try:
                table = {k: table_payload(sheet, columns, v) for k, v in rows.items()}
            finally:
                workbook.close()
            capture(gateway, state, table)
            _admit(gateway, state, roster)
    except Exception as exc:
        gateway.logger.warning("web_intake_unavailable reason=%s", exc)


def before_read(gateway):
    if not (gateway.root / "data" / DB_NAME).exists():
        return
    try:
        with gateway._session() as state:
            with Store(gateway.root) as store:
                register_runner(store)
                roster = store.meta("roster")
            if roster:
                _admit(gateway, state, roster)
    except Exception as exc:
        gateway.logger.warning("web_intake_unavailable reason=%s", exc)


def worker_bindings(gateway, bindings, accounts):
    # Keep every actually connected device reachable for later web submissions.
    # Unselected phones still receive None from the existing allocation-only read.
    with Store(gateway.root) as store:
        enabled = store.meta("enabled", False)
    return [dict(v) for v in bindings if accounts and (enabled or v["sender_account_id"] in accounts)]


def is_error(progress):
    # Mixed SUCCESS / NOT_FOUND also has aggregate FAILED, but is not a fault.
    return any(v.get("status") == "FAILED" for v in (progress or {}).get("accounts", []))


def ended_history(progress):
    value = core._copy(progress)
    now = core._utcnow().isoformat()
    for account in value["accounts"]:
        if account["status"] not in core.TERMINAL_STATUSES:
            account.update(status="FAILED", finished_at=now,
                           error_code="RUN_ENDED_BY_OPERATOR",
                           log_message="停止影刀后人工结束了未完成记录；此前已确认的成功次数保留")
    statuses = [v["status"] for v in value["accounts"]]
    value.update(completed=True, finished_device_count=len(statuses),
                 running_device_count=0, pending_device_count=0,
                 failed_device_count=statuses.count("FAILED"), status=core.UnifiedGateway._fixed_status(statuses))
    return value


def stopped_check(root, store):
    if any(process_stamp(v["pid"]) in (v["stamp"], "unknown-live") for v in store.meta("runners", [])):
        raise core.EngineError("EXECUTION_STILL_RUNNING", "影刀执行进程仍在运行；请先停止影刀运行")
    if os.name == "nt":
        # Also cover old executions made before the intake hooks were installed.
        script = "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
        result = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, timeout=15)
        if result.returncode:
            raise core.EngineError("STOP_CHECK_FAILED", "无法检查影刀执行进程，请关闭影刀后重新启动工具")
        values = json.loads(result.stdout.decode("utf-8-sig", errors="replace") or "[]")
        if isinstance(values, dict):
            values = [values]
        root_text = str(root).lower()
        for value in values:
            if value["ProcessId"] == os.getpid():
                continue
            name = (value.get("Name") or "").lower()
            command = (value.get("CommandLine") or "").lower()
            executable = (value.get("ExecutablePath") or "").lower()
            if ("python" in name or "engine" in name) and (root_text in command or executable.startswith(root_text + "\\")):
                raise core.EngineError("EXECUTION_STILL_RUNNING", "本项目影刀执行进程仍在运行")


def recover_cleanup(gateway, state):
    transaction = state.get("web_cleanup_transaction")
    if not transaction:
        return
    identity = transaction["task_id"]
    workbook, sheet, columns, rows, digest = read_book(gateway)
    try:
        if identity in rows:
            sheet.delete_rows(rows[identity])
            save_book(gateway, workbook, digest)
    finally:
        workbook.close()
    state["project_accounts"].pop(identity, None)
    state["relative_schedules"].pop(identity, None)
    if (state.get("pending_transaction") or {}).get("task_id") == identity:
        state["pending_transaction"] = None
    for device in state["devices"].values():
        if (device.get("active_task") or {}).get("task_id") == identity:
            device.update(state="READY", active_task=None, cooldown_until=None, block_info=None)
        if (device.get("last_result") or {}).get("task_id") == identity:
            device["last_result"] = None
    with Store(gateway.root) as store:
        store.db.execute("UPDATE records SET retained_only=1,intake_error='' WHERE task_id=?", (identity,))
        store.db.commit()
    state.pop("web_cleanup_transaction", None)
    state["exports_dirty"] = True
    gateway._save_state(state)
    for account in transaction["accounts"]:
        try:
            gateway._write_execution_data(state, account)
        except Exception as exc:
            gateway.logger.warning("web_cleanup_export_pending reason=%s", exc)


def cleanup(root, identity, owner, admin, stopped=False):
    identity = core._task_id(identity)
    gateway = gateway_for(root)
    # Do not replay an already failing Excel transaction before target cleanup.
    with gateway._session(recover=False) as state:
        if state.get("web_cleanup_transaction"):
            raise core.EngineError("CLEANUP_PENDING", "上一次清理尚未完成，请先重新打开工具")
        with Store(root) as store:
            record = store.row(identity)
            if not admin and (not record or record["owner"] != owner):
                raise core.EngineError("NOT_FOUND", "找不到这个任务")
            if record and record["retained_only"]:
                raise core.EngineError("NOT_FOUND", "任务已无运行记录需要清理")
            project = state["project_accounts"].get(identity)
            progress = gateway._project_progress(state, identity) if project else None
            active = any((v.get("active_task") or {}).get("task_id") == identity for v in state["devices"].values())
            workbook, sheet, columns, rows, _ = read_book(gateway)
            try:
                row = rows.get(identity)
                status = core._text(sheet.cell(row, columns["Status"]).value).upper() if row else ""
                payload = table_payload(sheet, columns, row) if row else json.loads(record["payload"]) if record else {}
            finally:
                workbook.close()
            started = any(v.get("claimed_at") or v.get("finished_at") for v in (progress or {}).get("accounts", []))
            unfinished = active or status == "RUNNING" or bool(started and progress and not progress["completed"])
            malformed = status and status not in {v.value for v in core.TaskStatus}
            pending_write = (state.get("pending_transaction") or {}).get("task_id") == identity
            if not project and not row and not record:
                raise core.EngineError("NOT_FOUND", "找不到这个任务")
            if unfinished or malformed or pending_write:
                if not admin or not stopped:
                    raise core.EngineError("STOP_REQUIRED", "此任务存在未结束的运行残留，仅B本机停止影刀后可清理")
                stopped_check(root, store)
            elif not progress or not progress["completed"] or not is_error(progress):
                if not (admin and record and record["intake_error"] and stopped):
                    raise core.EngineError("NOT_AN_ERROR", "这个任务没有已结束的执行异常")
                stopped_check(root, store)
            # History is retained in the normal record store, never a log-save gate.
            store.db.execute("INSERT OR IGNORE INTO records(task_id,payload,submitted_at,admitted) VALUES (?,?,?,1)",
                             (identity, core._json(payload), core._utcnow().isoformat()))
            if progress:
                if unfinished:
                    progress = ended_history(progress)
                store.db.execute("UPDATE records SET progress=?,payload=? WHERE task_id=?",
                                 (core._json(progress), core._json(payload), identity))
            store.db.commit()
        accounts = set((project or {}).get("accounts", {}))
        accounts.update(k for k, v in state["devices"].items() if (v.get("active_task") or {}).get("task_id") == identity)
        state["web_cleanup_transaction"] = {"task_id": identity, "accounts": sorted(accounts)}
        gateway._save_state(state)
        recover_cleanup(gateway, state)
        warning = ""
        try:
            gateway._flush_exports(state)
        except Exception as exc:
            warning = "运行占用已清理；结果输出将在下次影刀读取时完成更新"
            gateway.logger.warning("web_cleanup_export_pending reason=%s", exc)
        return {"task_id": identity, "message": "该任务的运行记录和占用已清理，历史及错误仍可查看", "warning": warning}


def public_progress(progress):
    if not progress:
        return None
    keys = ("task_id", "target_device_count", "assigned_device_count", "finished_device_count", "completed", "status", "counts")
    result = {k: progress.get(k) for k in keys}
    result["accounts"] = [{k: entry.get(k) for k in ("sender_account_id", "physical_device_id", "status", "claimed_at", "finished_at", "counts", "error_code", "log_message", "executed_actions")}
                          for entry in progress.get("accounts", [])]
    return result


def _live_records(gateway, root, admin):
    warning, live, table = "", {}, {}
    with gateway._session(recover=False) as state:
        if state.get("web_cleanup_transaction"):
            recover_cleanup(gateway, state)
        try:
            workbook, sheet, columns, rows, _ = read_book(gateway)
            try:
                table = {identity: (table_payload(sheet, columns, row), core._text(sheet.cell(row, columns["Status"]).value).upper()) for identity, row in rows.items()}
                with Store(root) as store:
                    for identity, (payload, status) in table.items():
                        store.db.execute("INSERT OR IGNORE INTO records(task_id,payload,submitted_at,admitted) VALUES (?,?,?,1)",
                                         (identity, core._json(payload), (state["project_accounts"].get(identity, {}).get("assignment") or {}).get("allocated_at") or core._utcnow().isoformat()))
                    store.db.commit()
                capture(gateway, state, {k: v[0] for k, v in table.items()})
            finally:
                workbook.close()
        except Exception as exc:
            warning = str(exc) if admin else "运行数据暂不可读取；已提交的任务仍保留"
        for identity in state["project_accounts"]:
            live[identity] = gateway._project_progress(state, identity)
        active_ids = {(v.get("active_task") or {}).get("task_id") for v in state["devices"].values()}
        pending_write_id = (state.get("pending_transaction") or {}).get("task_id")
    return warning, live, table, active_ids, pending_write_id


def records(root, owner, admin):
    gateway = gateway_for(root)
    readable = True
    try:
        warning, live, table, active_ids, pending_write_id = _live_records(gateway, root, admin)
    except Exception as exc:
        warning = str(exc) if admin else "运行数据暂不可读取；已提交的任务及历史仍保留"
        live, table, active_ids, pending_write_id, readable = {}, {}, set(), None, False
    with Store(root) as store:
        output = []
        for record in store.rows(owner, admin):
            identity = record["task_id"]
            payload = json.loads(record["payload"])
            progress = live.get(identity) or (json.loads(record["progress"]) if record["progress"] else None)
            row_status = table.get(identity, ({}, ""))[1]
            started = any(v.get("claimed_at") or v.get("finished_at") for v in (progress or {}).get("accounts", []))
            interrupted = identity in active_ids or row_status == "RUNNING" or bool(started and progress and not progress["completed"]) or identity == pending_write_id
            malformed = bool(row_status and row_status not in {v.value for v in core.TaskStatus})
            ended_error = bool(progress and progress["completed"] and is_error(progress))
            can_clean = readable and not record["retained_only"] and ((ended_error and not interrupted) or (admin and (interrupted or malformed or record["intake_error"])))
            intake_error = record["intake_error"]
            if intake_error and not admin and "执行设备数量超过本次影刀可用连接数量" not in intake_error:
                intake_error = "任务接入未完成，请联系B电脑查看具体原因；提交已保留"
            output.append({"task_id": identity, "submitted_at": record["submitted_at"],
                           "source_ip": record["source_ip"] if admin else "",
                           "payload": payload, "status": (progress or {}).get("status") or row_status or "PENDING",
                           "admitted": bool(record["admitted"]), "progress": public_progress(progress),
                           "intake_error": intake_error, "can_cleanup": bool(can_clean),
                           "requires_stop": bool(can_clean and (interrupted or malformed or record["intake_error"]))})
    return {"records": output, "warning": warning}


def _log_errors(path, source):
    if not path.exists():
        return []
    # Overall raw logs are local-admin-only; keep the most recent 512 KiB.
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 524288))
        text = stream.read().decode("utf-8-sig", errors="replace")
    groups, current = [], None
    for line in text.splitlines():
        header = bool(re.match(r"^\d{4}-\d{2}-\d{2}.*(?:\b(?:INFO|ERROR|WARNING)\b|\[(?:INFO|ERROR|WARN)\])", line))
        if header:
            if current:
                groups.append(current)
            current = {"recorded_at": line[:23], "task_id": "", "source": source, "log_message": line} if re.search(r"\bERROR\b|\[ERROR\]", line) else None
        elif current and len(current["log_message"]) < 16000:
            current["log_message"] += "\n" + line
    if current:
        groups.append(current)
    return groups[-200:]


def errors(root, owner, admin, task_id=None):
    data = records(root, owner, admin)
    allowed = {v["task_id"]: v for v in data["records"]}
    if task_id is not None and task_id not in allowed:
        raise core.EngineError("NOT_FOUND", "找不到这个任务")
    output = []
    path = Path(root) / "logs" / "execution_errors.jsonl"
    if path.exists():
        with path.open(encoding="utf-8-sig", errors="replace") as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                    identity = core._text(value.get("task_id"))
                    if identity not in allowed and not admin:
                        continue
                    if task_id is not None and identity != task_id:
                        continue
                    output.append({k: value.get(k, "") for k in ("recorded_at", "task_id", "sender_account_id", "physical_device_id", "error_code", "log_message", "executed_actions")})
                except (ValueError, AttributeError, core.EngineError):
                    continue
    for identity, record in allowed.items():
        if task_id is not None and identity != task_id:
            continue
        if record["intake_error"]:
            output.append({"task_id": identity, "recorded_at": record["submitted_at"], "source": "任务接入", "log_message": record["intake_error"]})
        for account in (record["progress"] or {}).get("accounts", []):
            if account["status"] != "FAILED":
                continue
            value = dict(task_id=identity, recorded_at=account["finished_at"], source="执行结果",
                         sender_account_id=account["sender_account_id"], physical_device_id=account["physical_device_id"],
                         error_code=account["error_code"], log_message=account["log_message"], executed_actions=account["executed_actions"])
            if not any(v.get("task_id") == identity and v.get("sender_account_id") == value["sender_account_id"] and v.get("error_code") == value["error_code"] and v.get("log_message") == value["log_message"] for v in output):
                output.append(value)
    if admin and task_id is None:
        output += _log_errors(Path(root) / "logs" / "execution.log", "业务日志")
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            folder = Path(local_appdata) / "ShadowBot" / "log"
            candidates = sorted(folder.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True) if folder.exists() else []
            if candidates:
                output += _log_errors(candidates[0], "影刀运行日志")
    output.sort(key=lambda v: str(v.get("recorded_at") or ""), reverse=True)
    return {"errors": output, "warning": data["warning"]}
