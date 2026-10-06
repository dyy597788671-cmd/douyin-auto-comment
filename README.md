# 影刀抖音搜索与作者核验

当前定稿：2026-10-06-FINAL-1。新会话从[NEW_SESSION_START.md](NEW_SESSION_START.md)开始，按[FLOW_PLAN.md](FLOW_PLAN.md)实施。

| 文件 | 用途 |
|---|---|
| NEW_SESSION_START.md | 新会话交接及第一批操作 |
| FLOW_PLAN.md | 最终104行配置、固定修改批次及验证边界 |
| flow-plan.json | 与行表一致的结构化步骤 |
| CURRENT_FLOW.md / CURRENT_FLOW.png | 用户当前原61行记录及拼接图 |
| module1.baseline.py | 用户当前影刀模块源码快照 |
| module1.py | 保留原接口，增加导航坐标和候选XPath纯计算函数的待替换模块 |
| FLOW_EXECUTION.md | 实际修改与测试进度 |

先按表格作品类型查视频或图文，到底仍未找到再查综合；三个栏目复用筛选、昵称初筛、封面定位和主页ID核验。顶部导航支持限定区域横向滑动。ID不同跳过卡片继续，查完仍无匹配提示“抖音号不同”。企业号与随机互动保留后续接入。

当前手机流程仍是原61行，新定稿尚未在用户电脑实施或手机实测。本仓库保存当前模块与流程交接，不构成包含core_runner及影刀客户端的完整独立运行包。
