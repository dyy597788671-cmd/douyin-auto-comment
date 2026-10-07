import csv
import json
import logging
import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core_runner as core
from openpyxl import Workbook


@contextmanager
def temporary_root():
    with tempfile.TemporaryDirectory() as folder:
        try:
            yield folder
        finally:
            root = Path(folder).resolve()
            for logger in list(logging.Logger.manager.loggerDict.values()):
                if isinstance(logger, logging.Logger):
                    for handler in list(logger.handlers):
                        if isinstance(handler, logging.FileHandler) and root in Path(handler.baseFilename).parents:
                            logger.removeHandler(handler)
                            handler.close()


def prepare_root(root, accounts):
    (root / "config").mkdir()
    (root / "data").mkdir()
    settings = {"sender_accounts": accounts, "share_probability": 1.0,
                "cooldown_min_seconds": 0, "cooldown_max_seconds": 0}
    (root / "config" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(core.HEADERS) + ["Expected_Douyin_ID", "Content_Type", "Comments"])
    sheet.append(["1005", "关键词", "作者", 0, "PENDING", None, None, "12345", "图文",
                  "\n".join("评论" + str(index) for index in range(len(accounts)))])
    workbook.save(root / "data" / "task_cases.xlsx")
    workbook.close()


def claim_and_plan(root, account):
    gateway = core.UnifiedGateway(str(root), device_id=account)
    task = gateway.get_next_task()
    plan = gateway.generate_strategy(seed=17, task_id=task["task_id"], run_token=task["run_token"])
    results = [{"action": action, "status": "PASSED", "message": ""}
               for action in plan["execution_order"]]
    return gateway, task, results


def finish_kwargs(task, actions, status="SUCCESS"):
    return {"task_id": task["task_id"], "run_token": task["run_token"],
            "status": status, "executed_actions": actions}


def read_rows(root, account):
    with (root / "execution_data" / ("执行数据_" + account + ".csv")).open(
            encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def finish_worker(root, account):
    gateway, task, actions = claim_and_plan(Path(root), account)
    gateway.record_result(**finish_kwargs(task, actions))


class ExecutionOutputTests(unittest.TestCase):
    def test_account_files_and_success_counts(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, ["手机01", "手机02"])
            for account in ("手机01", "手机02"):
                gateway, task, actions = claim_and_plan(root, account)
                self.assertEqual(actions[-1]["action"], "Share")
                if account == "手机02":
                    actions[-1]["status"] = "FAILED"
                gateway.record_result(**finish_kwargs(task, actions,
                    "SUCCESS" if account == "手机01" else "FAILED"))
            for account in ("手机01", "手机02"):
                rows = read_rows(root, account)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["执行账号"], account)
                self.assertEqual(rows[0]["项目ID"], "1005")
                self.assertEqual([rows[0][key] for key in ("点赞次数", "收藏次数", "评论次数")],
                                 ["1", "1", "1"])
                self.assertEqual(rows[0]["分享次数"], "1" if account == "手机01" else "0")

    def test_retry_and_restart_keep_one_row(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, ["手机01"])
            gateway, task, actions = claim_and_plan(root, "手机01")
            arguments = finish_kwargs(task, actions)
            first = gateway.record_result(**arguments)
            self.assertEqual(first, gateway.record_result(**arguments))
            restarted = core.UnifiedGateway(str(root), device_id="手机01")
            self.assertEqual(first, restarted.record_result(**arguments))
            self.assertEqual(len(read_rows(root, "手机01")), 1)

    def test_unselected_share_is_zero(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, ["手机01"])
            settings_path = root / "config" / "settings.json"
            settings = json.loads(settings_path.read_text())
            settings["share_probability"] = 0
            settings_path.write_text(json.dumps(settings), encoding="utf-8")
            gateway, task, actions = claim_and_plan(root, "手机01")
            gateway.record_result(**finish_kwargs(task, actions))
            self.assertEqual(read_rows(root, "手机01")[0]["分享次数"], "0")

    def test_csv_failure_can_retry_without_repeating_actions(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, ["手机01"])
            gateway, task, actions = claim_and_plan(root, "手机01")
            arguments = finish_kwargs(task, actions)
            original_write = core._atomic_bytes
            def write(path, payload):
                if path.suffix == ".csv":
                    raise PermissionError("test file is open")
                return original_write(path, payload)
            with patch.object(core, "_atomic_bytes", side_effect=write):
                with self.assertRaises(core.EngineError) as raised:
                    gateway.record_result(**arguments)
                self.assertEqual(raised.exception.code, "EXECUTION_DATA_WRITE_FAILED")
            self.assertIsNone(gateway.get_active_task())
            gateway.record_result(**arguments)
            self.assertEqual(len(read_rows(root, "手机01")), 1)
            self.assertEqual(read_rows(root, "手机01")[0]["评论次数"], "1")

    def test_not_found_has_no_success_counts(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, ["手机01"])
            gateway = core.UnifiedGateway(str(root), device_id="手机01")
            task = gateway.get_next_task()
            gateway.record_result(**finish_kwargs(task, [], "NOT_FOUND"))
            row = read_rows(root, "手机01")[0]
            self.assertEqual([row[key] for key in ("点赞次数", "收藏次数", "评论次数", "分享次数")],
                             ["0", "0", "0", "0"])

    def test_export_only_this_account_and_one_success_per_action(self):
        with temporary_root() as folder:
            root = Path(folder)
            prepare_root(root, ["手机01"])
            gateway = core.UnifiedGateway(str(root), device_id="手机01")
            state = {"project_accounts": {
                "1005": {"accounts": {"手机01": {"result": {"executed_actions": [
                    {"action": "Like", "status": "PASSED"},
                    {"action": "Like", "status": "PASSED"},
                    {"action": "Comment", "status": "UNCERTAIN"}]}}}},
                "1006": {"accounts": {"手机02": {"result": {"executed_actions": []}}}},
                "1007": {"accounts": {"手机01": {"result": None}}}}}
            gateway._write_execution_data(state, "手机01")
            row, = read_rows(root, "手机01")
            self.assertEqual(row["点赞次数"], "1")
            self.assertEqual(row["评论次数"], "0")

    def test_concurrent_account_output(self):
        with temporary_root() as folder:
            root = Path(folder)
            accounts = ["手机01", "手机02", "手机03"]
            prepare_root(root, accounts)
            context = multiprocessing.get_context("spawn")
            processes = [context.Process(target=finish_worker, args=(str(root), account))
                         for account in accounts]
            for process in processes:
                process.start()
            for process in processes:
                process.join(30)
                if process.is_alive():
                    process.terminate()
                    process.join()
                self.assertEqual(process.exitcode, 0)
            for account in accounts:
                row, = read_rows(root, account)
                self.assertEqual(row["执行账号"], account)
                self.assertEqual(row["分享次数"], "1")


if __name__ == "__main__":
    unittest.main()
