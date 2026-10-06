# 影刀抖音搜索与作者核验

实现修订：2026-10-06-FINAL-2。当前已完成第1—3批配置，实际行数按修改记录推算87；完整目标107行，手机新流程未实测。

| 文件 | 用途 |
|---|---|
| NEW_SESSION_START.md | 当前下一步及已确认配置 |
| FLOW_PLAN.md / flow-plan.json | 最终107行目标与业务规则 |
| CURRENT_FLOW.md | 当前87行检查点和原61行历史基线 |
| CURRENT_FLOW.png | 原61行历史拼接图 |
| module1.baseline.py / module1.py | 原模块快照及已替换的辅助函数模块 |
| FLOW_EXECUTION.md | 完成批次、测试边界与待办 |

先按作品类型查视频/图文，真实到底未匹配再查综合。各栏目复用筛选、昵称初筛、同卡片封面定位和主页ID核验。顶部导航支持按名称查找及限定在栏目条内的坐标横向滑动；元素text用全局nav_section，每轮从current_section赋值。

ID不同继续查，查完仍无MATCH提示“抖音号不同”。企业及互动保留后续接入。本仓库不是包含core_runner及影刀客户端的完整独立运行包。
