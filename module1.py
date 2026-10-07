import sys

PROJECT_ROOT = r"D:\备份文件\项目库\抖音自动发布工具"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import core_runner


def read_task(sender_account_id="手机01", adopt_legacy=False, physical_device_id=None,
              resume_active=False):
    """每个发送账号使用固定且不同的标识；旧default-device只在明确指定时转交。"""
    gateway = core_runner.UnifiedGateway(
        root=PROJECT_ROOT,
        device_id=sender_account_id
    )
    if adopt_legacy:
        gateway.adopt_legacy_task()

    task = gateway.get_active_task(physical_device_id=physical_device_id)
    if task is not None:
        if physical_device_id is not None and not task.get("assignment_id"):
            raise RuntimeError("该账号仍有旧模式活动任务，请先核对处理，不能混入新的随机分配")
        if task.get("assignment_id") and not resume_active:
            raise RuntimeError("该账号的分配任务已领取；不能重复启动。明确核对后才允许恢复")
        if task.get("strategy") is not None:
            raise RuntimeError("已有互动策略，请先核对执行进度再恢复")
        return task

    return gateway.get_next_task(physical_device_id=physical_device_id)


def allocate_task(task_id, connected_devices):
    """影刀管理流程传入当前实际连接设备列表；本函数不连接或操作手机。"""
    roster = core_runner._connected_devices(connected_devices)
    gateway = core_runner.UnifiedGateway(PROJECT_ROOT, roster[0]["sender_account_id"])
    return gateway.allocate_task(task_id, roster)


def project_progress(task_id, sender_account_id="手机01"):
    """供后续前端读取固定分配名单、结束数量、实际计数与各设备结果。"""
    return core_runner.UnifiedGateway(PROJECT_ROOT, sender_account_id).get_project_progress(task_id)


def verify_author(task_data, profile_douyin_id_raw, profile_author_name_raw):
    if not isinstance(task_data, dict):
        raise ValueError("task_data 必须是当前任务对象")

    gateway = core_runner.UnifiedGateway(
        root=PROJECT_ROOT,
        device_id=task_data["sender_account_id"]
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
        device_id=task_data["sender_account_id"]
    )
    plan = gateway.generate_strategy(task_id=task_id, run_token=run_token)
    plan["content_type"] = content_type
    return plan


def record_action_result(executed_actions, action, status, message="", task_data=None):
    """保存影刀确认后的动作结果到返回列表；本函数不点击或发送。"""
    if not isinstance(executed_actions, list):
        raise ValueError("executed_actions 必须是列表")
    result = executed_actions + [{
        "action": action,
        "status": status,
        "message": message
    }]
    result = core_runner.UnifiedGateway._actions(result)
    if task_data is not None:
        if not isinstance(task_data, dict):
            raise ValueError("task_data 必须是当前任务对象")
        gateway = core_runner.UnifiedGateway(PROJECT_ROOT, task_data["sender_account_id"])
        return gateway.save_action_results(task_data["task_id"], task_data["run_token"], result)
    return result


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
        device_id=task_data["sender_account_id"]
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


def build_author_cover_xpath(expected_author, occurrence=1):
    """生成同一卡片内的目标作者封面XPath；occurrence从1开始。"""
    if not isinstance(expected_author, str) or not expected_author:
        raise ValueError("expected_author 必须是非空昵称")
    if isinstance(occurrence, bool) or not isinstance(occurrence, int) or occurrence < 1:
        raise ValueError("occurrence 必须是从1开始的整数")
    # 复用封面层级，以可点击层识别封面，不固定index或resource-id。
    author_literal = "concat(''," + ", \"'\", ".join(
        "'" + part + "'" for part in expected_author.split("'")
    ) + ")"
    cover_tail = "/android.widget.FrameLayout/android.view.ViewGroup/android.view.View[@clickable='true']"
    cover = (
        "/hierarchy//androidx.recyclerview.widget.RecyclerView"
        "/android.widget.LinearLayout/android.widget.LinearLayout/android.widget.LinearLayout"
        + cover_tail
    )
    relative_cover = ".//" + cover_tail[1:]
    same_card = (
        "ancestor::android.widget.LinearLayout["
        "ancestor::androidx.recyclerview.widget.RecyclerView and "
        "count(" + relative_cover + ")=1 and .//*[@text=" + author_literal + "]]"
    )
    base = cover + "[" + same_card + "]"
    return "(" + base + ")[" + str(occurrence) + "]"


def make_nav_swipe_points(bounds):
    """只计算坐标，不连接或操作手机；输入安卓bounds属性。"""
    import re
    if isinstance(bounds, str):
        match = re.fullmatch(r"\s*\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]\s*", bounds)
        if not match:
            raise ValueError("导航bounds格式应为[left,top][right,bottom]")
        left, top, right, bottom = map(int, match.groups())
    elif isinstance(bounds, dict):
        left, top, right, bottom = (bounds[key] for key in ("left", "top", "right", "bottom"))
    else:
        raise ValueError("导航bounds必须是安卓bounds字符串或边界字典")
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (left, top, right, bottom)):
        raise ValueError("导航边界必须是整数")
    if left < 0 or top < 0 or right - left < 10 or bottom - top < 2:
        raise ValueError("导航区域边界无效")
    middle_y = (top + bottom) // 2
    left_x = left + (right - left) * 20 // 100
    right_x = left + (right - left) * 80 // 100
    return {
        "left": {"start_x": right_x, "start_y": middle_y, "end_x": left_x, "end_y": middle_y},
        "right": {"start_x": left_x, "start_y": middle_y, "end_x": right_x, "end_y": middle_y},
    }

