"""Patch only known intake boundaries; preserve the installed B module root."""
import argparse
import ast
import shutil
import textwrap
from datetime import datetime
from pathlib import Path

MARKER = "# LAN_TOOL_INTAKE_V1"


def patch_core(source):
    if MARKER in source:
        return source
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "UnifiedGateway")
    functions = {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}
    allocate = functions["allocate_task"]
    block = allocate.body[-1]
    expression = block.items[0].context_expr if isinstance(block, ast.With) else None
    if not isinstance(expression, ast.Call) or not isinstance(expression.func, ast.Attribute) or expression.func.attr != "_session":
        raise RuntimeError("设备分配函数与已核对版本不同，未修改")
    lines = source.splitlines(keepends=True)
    body = "".join(lines[block.body[0].lineno - 1:block.end_lineno])
    # Copy the existing allocation algorithm byte for byte, reducing one indent.
    body = "".join(line[4:] if line.startswith("    ") else line for line in body.splitlines(keepends=True))
    replacement = "        with self._session() as state:\n            return self._allocate_task_locked(state, identity, roster)\n\n    def _allocate_task_locked(self, state, identity, roster):\n        " + MARKER + "\n        configured = self.settings[\"sender_accounts\"]\n        if configured and any(v[\"sender_account_id\"] not in configured for v in roster):\n            raise EngineError(\"ACCOUNT_NOT_CONFIGURED\", \"连接名单含未登记的执行账号\")\n" + body
    lines[block.lineno - 1:block.end_lineno] = [replacement]
    source = "".join(lines)
    old = "                state = self._load_state()\n                if recover:"
    new = "                state = self._load_state()\n                if state.get(\"web_cleanup_transaction\"):\n                    import lan_bridge\n                    lan_bridge.recover_cleanup(self, state)\n                if recover:"
    if source.count(old) != 1:
        raise RuntimeError("项目锁入口与已核对版本不同，未修改")
    source = source.replace(old, new)
    old = "        state[\"exports_dirty\"] = False\n        self._save_state(state)"
    new = old + "\n        try:\n            import lan_bridge\n            lan_bridge.snapshot(self, state)\n        except ImportError:\n            pass"
    if source.count(old) != 1:
        raise RuntimeError("执行结果输出入口与已核对版本不同，未修改")
    source = source.replace(old, new)
    ast.parse(source)
    return source


def patch_module(source):
    if MARKER in source:
        return source
    # Match the actual established API instead of replacing the whole module.
    tree = ast.parse(source)
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    if not {"read_task", "prepare_devices", "finish_task"}.issubset(names):
        raise RuntimeError("当前module1缺少已核对的接口，未修改")
    changes = {
        "    task = gateway.get_active_task(physical_device_id=physical_device_id)":
        "    import lan_bridge\n    lan_bridge.before_read(gateway)\n    task = gateway.get_active_task(physical_device_id=physical_device_id)",
        "        task = gateway.get_next_task(physical_device_id=physical_device_id)":
        "        lan_bridge.before_read(gateway)\n        task = gateway.get_next_task(physical_device_id=physical_device_id)",
        "    gateway = core_runner.UnifiedGateway(PROJECT_ROOT, roster[0][\"sender_account_id\"])\n    workbook, sheet, columns, rows, _ = gateway.scheduler.read()":
        "    gateway = core_runner.UnifiedGateway(PROJECT_ROOT, roster[0][\"sender_account_id\"])\n    import lan_bridge\n    lan_bridge.prepare(gateway, roster)\n    workbook, sheet, columns, rows, _ = gateway.scheduler.read()",
        "        return [dict(binding) for binding in bindings if binding[\"sender_account_id\"] in accounts]":
        "        return lan_bridge.worker_bindings(gateway, bindings, accounts)",
    }
    for old, new in changes.items():
        if source.count(old) != 1:
            raise RuntimeError("当前module1接入位置与已核对版本不同，未修改")
        source = source.replace(old, new)
    source += "\n" + MARKER + "\n"
    ast.parse(source)
    return source


def install(root, package):
    root, package = Path(root).resolve(), Path(package).resolve()
    core_path, module_path = root / "core_runner.py", root / "xbot_robot" / "module1.py"
    for path in (core_path, module_path, root / "data" / "task_cases.xlsx"):
        if not path.is_file():
            raise RuntimeError("缺少B项目文件：" + str(path))
    original_core = core_path.read_text(encoding="utf-8-sig")
    original_module = module_path.read_text(encoding="utf-8-sig")
    new_core, new_module = patch_core(original_core), patch_module(original_module)
    backup = root / "tool-backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True)
    for path in (core_path, module_path, root / "lan_bridge.py"):
        if path.exists():
            shutil.copy2(path, backup / path.name)
    try:
        shutil.copy2(package / "lan_bridge.py", root / "lan_bridge.py")
        shutil.copytree(package / "lan_tool", root / "lan_tool", dirs_exist_ok=True)
        core_path.write_text(new_core, encoding="utf-8")
        module_path.write_text(new_module, encoding="utf-8")
    except Exception:
        for path in (core_path, module_path):
            shutil.copy2(backup / path.name, path)
        raise
    print("BACKUP=" + str(backup))
    print("RESULT=TOOL_INSTALLED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--package", default=str(Path(__file__).parent))
    args = parser.parse_args()
    install(args.root, args.package)
