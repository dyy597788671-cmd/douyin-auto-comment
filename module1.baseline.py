import sys

PROJECT_ROOT = r"D:\备份文件\项目库\抖音自动发布工具"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import core_runner


def read_task():
    gateway = core_runner.UnifiedGateway(
        root=PROJECT_ROOT,
        device_id="default-device"
    )

    task = gateway.get_active_task()
    if task is not None:
        if task.get("strategy") is not None:
            raise RuntimeError("已有互动策略，请先核对执行进度再恢复")
        return task

    return gateway.get_next_task()


def verify_author(task_data, profile_douyin_id_raw, profile_author_name_raw):
    if not isinstance(task_data, dict):
        raise ValueError("task_data 必须是当前任务对象")

    gateway = core_runner.UnifiedGateway(
        root=PROJECT_ROOT,
        device_id="default-device"
    )

    return gateway.assert_author(
        expected={
            "douyin_id": task_data.get("expected_douyin_id"),
            "nickname": task_data.get("expected_author"),
            "source": "verified"
        },
        actual={
            "douyin_id": profile_douyin_id_raw,
            "nickname": profile_author_name_raw,
            "source": "ui"
        }
    )


def prepare_interactions(task_data):
    """作者核验成功后调用；复用底层策略，不执行手机操作。"""
    if not isinstance(task_data, dict):
        raise ValueError("task_data 必须是当前任务对象")
    content_type = task_data.get("content_type")
    if content_type not in ("视频", "图文"):
        raise ValueError("任务 Content_Type 必须填写视频或图文")
    task_id = task_data.get("task_id")
    run_token = task_data.get("run_token")
    if not task_id or not run_token:
        raise ValueError("当前任务缺少 task_id 或 run_token")

    gateway = core_runner.UnifiedGateway(
        root=PROJECT_ROOT,
        device_id="default-device"
    )
    plan = gateway.generate_strategy(task_id=task_id, run_token=run_token)
    plan["content_type"] = content_type
    return plan


def record_action_result(executed_actions, action, status, message=""):
    """保存影刀确认后的动作结果到返回列表；本函数不点击或发送。"""
    if not isinstance(executed_actions, list):
        raise ValueError("executed_actions 必须是列表")
    result = executed_actions + [{
        "action": action,
        "status": status,
        "message": message
    }]
    return core_runner.UnifiedGateway._actions(result)


def finish_task(task_data, executed_actions, status="SUCCESS",
                error_code="", log_message=""):
    """回写实际结果；SUCCESS 由底层校验动作顺序与结果。"""
    if not isinstance(task_data, dict):
        raise ValueError("task_data 必须是当前任务对象")
    task_id = task_data.get("task_id")
    run_token = task_data.get("run_token")
    if not task_id or not run_token:
        raise ValueError("当前任务缺少 task_id 或 run_token")
    gateway = core_runner.UnifiedGateway(
        root=PROJECT_ROOT,
        device_id="default-device"
    )
    return gateway.record_result(
        task_id=task_id,
        status=status,
        executed_actions=executed_actions,
        error_code=error_code,
        log_message=log_message,
        run_token=run_token
    )


def main(args=None):
    return read_task()
