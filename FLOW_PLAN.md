# 影刀主流程逐行定稿

版本：2026-10-06-FINAL-3。用户业务规则定稿于北京时间2026-10-06 15:54；用户15:58授权保存、同步GitHub，新会话逐行实施。

最终目标及当前配置均为109行；原始基线61行。北京时间2026-10-06 18:52，用户已逐项确认第1—5批配置完成；当前1—98启用、99—109禁用。实际总数按修改链推算，尚无全流程导出复核和新流程手机实测。保留原昵称IF外层，候选ForEach位于其内部，原核验动作复用；业务规则不变。

## 已定规则

- 一个主流程，不另拆三套综合/视频/图文流程；统一三层循环：栏目、逐屏、同屏候选。
- search_sections取[表格content_type, 综合]；content_type只能是视频/图文，原search_section不再控制优先查找。
- 先查对应类型栏目，真实到底仍未匹配才查综合；综合重复执行同一筛选，不直接沿用前栏目筛选状态。
- 顶部栏目按名称定位，横向滑动限定于栏目条。综合优先向右滑找左侧栏目；其他栏目优先向左滑显示右侧。首方向未找到再反方向找。12次只用于单方向导航异常上限，与结果分页无关。
- 筛选保留原顺序及图像：最新发布 → 一天内 → 红底查看结果。
- 先读取本屏昵称，按精确昵称筛出候选；同屏多个同名卡片逐个核验。封面按原24行同卡片XPath匹配序号定位，不使用两个独立列表的索引去拼对应关系。
- 进作品 → 按视频/图文头像进主页 → 读取抖音号及昵称 → verify_author → 退回作品。ID匹配即停止三个搜索循环。
- ID不同：保存saw_id_mismatch=True，退回结果继续当前屏其他候选和后续屏；类型栏目查完再查综合；两栏目仍无MATCH提示用户原文“抖音号不同”。
- 普通ID读取指令异常自然停止，不新增失败IF、重试、兜底或异常恢复；原UNCERTAIN核验报错块保留。
- 企业号本轮不处理，用户自行处理；只留将来的ID读取适配位置，不加企业识别或专项步骤。
- 末尾标记为原46行“暂无更多，查看所有内容”。先处理末屏候选，再退出；不点击“查看所有内容”扩大时间范围。
- 本阶段不生成互动策略，不调用finish_task回写成功，不把“作者已核验”记为“互动已完成”。

## 修改前准备与元素绑定

用户已自行备份并替换影刀应用内module1。仓库module1.py仅在原模块末尾增加两个纯计算函数，原read_task/verify_author/prepare_interactions/record_action_result/finish_task实现保持原样。以后不要重复要求备份或替换模块。

| 元素/图片 | 处理 |
|---|---|
| 搜索结果作者昵称 | 使用用户已实测正确的现有条目；不要重抓，不恢复已删除的目标作者昵称/作者昵称 |
| 抖音搜索结果封面 | 保留已验证综合、视频、图文可用的条目，不重新抓重复封面；原24行定位方案改用模块生成的带匹配序号XPath |
| 抖音搜索入口、抖音搜索输入框、搜索按钮、抖音筛选入口 | 使用现有条目及已配置参数 |
| 图文作者头像、视频作者头像 | 保留分别的入口，必要分叉只放56—60行 |
| 抖音主页_账号、主页_作者昵称 | 保留现有条目；企业号暂不扩展 |
| 最新发布、一天内、查看结果、暂无更多查看所有内容 | 使用原16/17/18/46行图像与完整参数，移动原卡片，不重设截图或阈值 |
| 抖音搜索顶部栏目条（新增一次） | 第9行用结构XPath "//android.widget.HorizontalScrollView[.//androidx.appcompat.app.ActionBar.Tab]" 获取nav_container，第10行读取bounds；用户无法捕获整条容器，不再要求重抓容器 |
| 抖音搜索栏目（统一动态条目） | 从已有搜索分区_视频/图文定位规则统一，目标text由fx选择全局变量nav_section；第16行每轮将current_section赋给该全局变量，作用域限于顶部栏目条；同一个条目匹配视频/图文/综合，不按栏目位置和序号。不能把正文中同样的文字误作导航 |

导航配置已在用户编辑器中完成：动态栏目通过全局变量选择绑定；左右滑动使用栏目bounds计算出的屏幕坐标，区域选择“在整个屏幕中”，路径本身位于栏目条内部。新配置尚未手机实测，不能写已跑通。

## 变量与作用域

| 变量 | 类型 | 范围/约束 |
|---|---|---|
| task_data | 字典 | 当前任务，read_task返回 |
| target_author | 字符串 | task_data["expected_author"] |
| phone_device | 连接对象 | 原第3行返回，所有手机指令沿用 |
| nav_container | 手机元素对象 | 结构XPath获取的横向栏目容器 |
| nav_section | 全局字符串 | 默认文本图文；第16行从current_section赋值，元素text通过fx选择它；禁止手输变量名冒充绑定 |
| nav_exists | 布尔 | 第21行等待元素的结果；第22行普通IF判断 |
| nav_bounds_raw | 字符串/边界字典 | 当前手机顶部栏目容器实际边界 |
| nav_swipe_points | 字典 | make_nav_swipe_points返回，按实际手机边界计算，不用某机型绝对坐标 |
| search_sections | 列表 | [task_data["content_type"], "综合"] |
| current_section | 字符串 | 外层栏目循环当前值，不能替代作品类型 |
| saw_id_mismatch | 布尔 | 当前任务一次初始化，跨屏、跨栏目保留 |
| author_check_result | 字符串 | NOT_FOUND/MATCH/MISMATCH/UNCERTAIN，每次调用verify_author用其返回覆盖 |
| nav_found | 布尔 | 当前栏目切换状态 |
| nav_directions/nav_direction | 列表/字符串 | left表示手指向左滑，显示右側；right相反 |
| section_finished | 布尔 | 每栏目初始化False，看到真实末尾才True |
| author_name_list | 文本列表 | 每屏重新读取，不保留旧元素对象 |
| candidate_numbers/current_candidate_number | 列表/整数 | 当前屏匹配昵称序号，从1开始，不能跨屏继续使用 |
| candidate_xpath/mobile_element_result | 字符串/元素对象 | 当前候选，进入作品前重新获取 |
| is_tuwen | 布尔 | 依据task_data["content_type"]，查综合时也不改成综合 |
| profile_douyin_id_raw/profile_author_name_raw | 字符串 | 原主页元素读取结果，不改成内部UID |

## 最终行表

以下为最终目标，来源“原N”为原61行基线，不是当前行号。当前实际行表见CURRENT_FLOW.md。

| 最终行 | 影刀指令 | 配置与输出 | 来源 | 状态 |
|---|---|---|---|---|
| 1 | 调用模块 | module1.read_task() → task_data | 原1 | 启用 |
| 2 | 设置变量 | target_author = task_data["expected_author"]（字符串） | 原2 | 启用 |
| 3 | 连接手机 | 保留Appium、运行时手动选择 → phone_device；沿用现有参数 | 原3 | 启用 |
| 4 | 打开手机APP | phone_device；com.ss.android.ugc.aweme；激活到屏幕 | 原4 | 启用 |
| 5 | 等待 | 保留现有3—10秒 | 原5 | 启用 |
| 6 | 点击元素(手机) | 抖音搜索入口；单击中心；保留现有参数 | 原6 | 启用 |
| 7 | 输入文本(手机) | 抖音搜索输入框；task_data["keyword"]；phone_device | 原7 | 启用 |
| 8 | 点击元素(手机) | 搜索按钮；单击中心；保留现有参数 | 原8 | 启用 |
| 9 | 获取元素对象(手机) | phone_device；XPath "//android.widget.HorizontalScrollView[.//androidx.appcompat.app.ActionBar.Tab]" → nav_container | 新增 | 启用 |
| 10 | 获取手机元素信息 | phone_device；操作目标nav_container；获取属性bounds → nav_bounds_raw | 新增 | 启用 |
| 11 | 调用模块 | module1.make_nav_swipe_points(nav_bounds_raw) → nav_swipe_points | 新增 | 启用 |
| 12 | 设置变量 | search_sections = [task_data["content_type"], "综合"]（列表） | 新增 | 启用 |
| 13 | 设置变量 | saw_id_mismatch = False（布尔）；当前任务范围，仅初始化一次 | 新增 | 启用 |
| 14 | 设置变量 | author_check_result = "NOT_FOUND"（字符串） | 原19 | 启用 |
| 15 | ForEach列表循环 | 遍历search_sections → current_section；外层栏目循环 | 新增 | 启用 |
| 16 | 设置变量 | 字符串；变量值Python current_section；输出通过fx选择全局变量nav_section（glv["nav_section"]）；每轮栏目开始赋值 | 复制原2 | 启用 |
| 17 | 设置变量 | nav_found = False（布尔）；每轮栏目初始化 | 新增 | 启用 |
| 18 | 设置变量 | nav_directions = (["right", "left"] if current_section == "综合" else ["left", "right"])（列表） | 新增 | 启用 |
| 19 | ForEach列表循环 | 遍历nav_directions → nav_direction；仅处理顶部导航 | 新增 | 启用 |
| 20 | For次数循环 | 起始数1；结束数12；递增值1；当前循环项loop_index；仅为导航上限，不限制结果分页 | 新增 | 启用 |
| 21 | 等待元素(手机) | phone_device；已有抖音搜索栏目；等待元素出现；超时5秒 → nav_exists；错误处理默认（超时行为待手机实测） | 新增 | 启用 |
| 22 | IF 条件 | 对象1 Python nav_exists；关系等于；对象2 Python True | 原9复用 | 启用 |
| 23 | 点击元素(手机) | phone_device；已有抖音搜索栏目（text通过fx绑定全局nav_section）；单击中心点一次；点击后延迟1秒；等待元素存在5秒 | 原10复用 | 启用 |
| 24 | 设置变量 | nav_found = True（布尔） | 新增 | 启用 |
| 25 | 退出循环 | 退出20行次数循环 | 新增 | 启用 |
| 26 | Else | 对应22行 | 新增 | 启用 |
| 27 | IF 条件 | 对象1 Python nav_direction；关系等于；对象2 Python "left" | 新增 | 启用 |
| 28 | 滑动手机屏幕 | phone_device；在整个屏幕中；坐标；四项Python nav_swipe_points["left"]["start_x"/"start_y"/"end_x"/"end_y"]；滑动时间800毫秒；执行后延迟1秒；错误处理默认 | 复制原49，原49保留 | 启用 |
| 29 | Else | 对应27行 | 新增 | 启用 |
| 30 | 滑动手机屏幕 | phone_device；在整个屏幕中；坐标；四项Python nav_swipe_points["right"]["start_x"/"start_y"/"end_x"/"end_y"]；滑动时间800毫秒；执行后延迟1秒；错误处理默认 | 复制左滑 | 启用 |
| 31 | End IF | 结束27行 | 新增 | 启用 |
| 32 | End IF | 结束22行 | 新增 | 启用 |
| 33 | 循环结束标记 | 结束20行次数循环 | 新增 | 启用 |
| 34 | IF 条件 | nav_found 等于True | 原12复用 | 启用 |
| 35 | 退出循环 | 退出19行方向循环 | 复制导航退出循环，替换原13点击 | 启用 |
| 36 | End IF | 结束34行 | 新增 | 启用 |
| 37 | 循环结束标记 | 结束19行方向循环 | 新增 | 启用 |
| 38 | IF 条件 | nav_found 等于False | 新增 | 启用 |
| 39 | Raise | "未找到搜索栏目：" + current_section；定位异常终止，不冒充结果到底 | 新增 | 启用 |
| 40 | End IF | 结束38行 | 新增 | 启用 |
| 41 | 点击元素(手机) | 抖音筛选入口；保留原参数 | 原15 | 启用 |
| 42 | 点击屏幕(手机) | 原“最新发布”匹配图与原参数，不改为固定坐标 | 原16 | 启用 |
| 43 | 点击屏幕(手机) | 原“一天内”匹配图与原参数 | 原17 | 启用 |
| 44 | 点击屏幕(手机) | 原红底“查看结果”匹配图与原参数 | 原18 | 启用 |
| 45 | 设置变量 | section_finished = False（布尔） | 新增 | 启用 |
| 46 | While条件循环 | (not section_finished) and author_check_result != "MATCH" 等于True；结果逐屏循环 | 原20复用 | 启用 |
| 47 | 获取相似元素列表(手机) | 搜索结果作者昵称；读取文本 → author_name_list；复用已验证元素 | 原21 | 启用 |
| 48 | 打印日志 | 信息；Python "栏目=" + repr(current_section) + "；目标昵称=" + repr(task_data["expected_author"]) + "；本屏读取昵称=" + repr(author_name_list) | 原22 | 启用 |
| 49 | 设置变量 | 列表；Python list(range(1, author_name_list.count(task_data["expected_author"]) + 1)) → candidate_numbers | 新增 | 启用 |
| 50 | IF 条件 | Python task_data["expected_author"] in author_name_list 等于 Python True；保留原昵称判断，候选循环放在内部 | 原23保留 | 启用 |
| 51 | ForEach列表循环 | Python candidate_numbers → current_candidate_number；在50行昵称IF内遍历同屏候选 | 新增 | 启用 |
| 52 | 调用模块 | module1.build_author_cover_xpath(expected_author=task_data["expected_author"], occurrence=current_candidate_number)；返回值类型字符串 → candidate_xpath | 新增 | 启用 |
| 53 | 获取元素对象(手机) | phone_device；查找方式XPath；XPath值Python candidate_xpath → mobile_element_result；复用原获取元素对象卡片 | 原24 | 启用 |
| 54 | 点击元素(手机) | mobile_element_result；单击中心；保留原参数 | 原25 | 启用 |
| 55 | 设置变量 | is_tuwen = (task_data["content_type"] == "图文")（布尔）；与current_section分开 | 原26 | 启用 |
| 56 | IF 条件 | is_tuwen 等于True | 原27 | 启用 |
| 57 | 点击元素(手机) | 图文作者头像；保留原参数 | 原28 | 启用 |
| 58 | Else | 对应56行 | 原29 | 启用 |
| 59 | 点击元素(手机) | 视频作者头像；保留原参数 | 原30 | 启用 |
| 60 | End IF | 结束56行 | 原31 | 启用 |
| 61 | 获取手机元素信息 | 抖音主页_账号；文本 → profile_douyin_id_raw；读取异常自然停止 | 原32 | 启用 |
| 62 | 获取手机元素信息 | 主页_作者昵称；文本 → profile_author_name_raw | 原33 | 启用 |
| 63 | 调用模块 | module1.verify_author；传task_data/profile_douyin_id_raw/profile_author_name_raw → author_check_result；沿用已确认设置 | 原34 | 启用 |
| 64 | 点击按键 | phone_device；后退；从作者主页返回作品 | 原35 | 启用 |
| 65 | IF 条件 | author_check_result 等于"MATCH" | 原36 | 启用 |
| 66 | 退出循环 | 退出51行当前屏候选循环 | 原37 | 启用 |
| 67 | End IF | 结束65行 | 原38 | 启用 |
| 68 | IF 条件 | author_check_result 等于"MISMATCH" | 原39 | 启用 |
| 69 | 设置变量 | saw_id_mismatch = True（布尔）；之后不因滑屏或切栏目清空 | 新增 | 启用 |
| 70 | 点击按键 | phone_device；后退；从作品返回当前栏目结果；继续下一候选 | 原40 | 启用 |
| 71 | End IF | 结束68行 | 原41 | 启用 |
| 72 | IF 条件 | author_check_result 等于"UNCERTAIN"；保留原有核验不确定处理，不增加读取失败IF | 原42 | 启用 |
| 73 | Raise | 作者抖音号核验不确定，请检查任务表中的抖音号及主页读取结果 | 原43 | 启用 |
| 74 | End IF | 结束72行 | 原44 | 启用 |
| 75 | 循环结束标记 | 结束51行候选循环 | 新增 | 启用 |
| 76 | End IF | 结束50行原昵称IF；保留其外层结构 | 原45保留 | 启用 |
| 77 | IF 条件 | author_check_result 等于"MATCH" | 新增 | 启用 |
| 78 | 退出循环 | 退出46行逐屏循环 | 新增 | 启用 |
| 79 | End IF | 结束77行 | 新增 | 启用 |
| 80 | IF 图像存在(手机) | 原“暂无更多，查看所有内容”匹配图与原参数；先处理完本屏候选再判到底 | 原46 | 启用 |
| 81 | 设置变量 | section_finished = True（布尔） | 新增 | 启用 |
| 82 | 退出循环 | 退出46行逐屏循环 | 原47 | 启用 |
| 83 | End IF | 结束80行 | 原48 | 启用 |
| 84 | 滑动手机屏幕 | 向上滑动结果列表；保留原49参数；不滑顶部导航 | 原49 | 启用 |
| 85 | 循环结束标记 | 结束46行逐屏循环 | 原50 | 启用 |
| 86 | IF 条件 | author_check_result 等于"MATCH" | 新增 | 启用 |
| 87 | 退出循环 | 退出15行栏目循环，不再查综合 | 新增 | 启用 |
| 88 | End IF | 结束86行 | 新增 | 启用 |
| 89 | 循环结束标记 | 结束15行栏目循环；只有类型栏目到底未匹配才进入综合 | 新增 | 启用 |
| 90 | IF 条件 | author_check_result 等于"MATCH" | 新增 | 启用 |
| 91 | 打印日志 | 作者抖音号核验成功；当前保留作品页，尚未执行互动 | 新增 | 启用 |
| 92 | Else | 对应90行 | 新增 | 启用 |
| 93 | IF 条件 | saw_id_mismatch 等于True | 新增 | 启用 |
| 94 | 打印日志 | 抖音号不同；仅两个栏目查完仍无MATCH才到此处 | 新增 | 启用 |
| 95 | Else | 对应93行 | 新增 | 启用 |
| 96 | 打印日志 | 未找到目标作品；只用于全程未遇到ID不同且没有MATCH | 新增 | 启用 |
| 97 | End IF | 结束93行 | 新增 | 启用 |
| 98 | End IF | 结束90行 | 新增 | 启用 |
| 99 | IF 条件 | author_check_result 等于"MATCH"；整个后续互动块暂禁用 | 原51 | 禁用 |
| 100 | 调用模块 | module1.prepare_interactions(task_data) → interaction_plan；本阶段禁用 | 原52 | 禁用 |
| 101 | 设置变量 | executed_actions = []；本阶段禁用 | 原53 | 禁用 |
| 102 | ForEach列表循环 | interaction_plan["execution_order"] → current_action；本阶段禁用，恢复时核实实际键名 | 原54 | 禁用 |
| 103 | IF 条件 | current_action 等于"Like"；本阶段禁用 | 原55 | 禁用 |
| 104 | IF 条件 | interaction_plan["content_type"] 等于"视频"；本阶段禁用 | 原56 | 禁用 |
| 105 | 获取手机元素信息 | 视频——点赞按钮；原属性参数 → like_state_raw；本阶段禁用 | 原57 | 禁用 |
| 106 | End IF | 结束104行；本阶段禁用 | 原58 | 禁用 |
| 107 | End IF | 结束103行；本阶段禁用 | 原59 | 禁用 |
| 108 | 循环结束标记 | 结束102行；本阶段禁用 | 原60 | 禁用 |
| 109 | End IF | 结束99行；本阶段禁用 | 原61 | 禁用 |

## 循环及退出目标

| 循环起始 | 结束 | 成功/退出行为 |
|---|---|---|
| 15 | 89 | 87退出栏目循环，第一栏目MATCH后不查综合 |
| 19 | 37 | 35退出方向循环 |
| 20 | 33 | 25退出导航次数循环 |
| 46 | 85 | 78为MATCH退出；82为真实末尾退出 |
| 51 | 75 | 66为MATCH退出；MISMATCH继续 |
| 102 | 108 | 互动循环整体禁用 |

原昵称IF和End IF保留在50/76，候选循环位于其中。原核验分叉、结果滑动和已验证元素全部复用。截图右键菜单无直接替换入口，不要求删除整个含内部动作的块。

## 修改执行批次（业务顺序不变）

1. 已完成：备份、模块替换、导航绑定、旧互动块禁用。
2. 已完成：导航边界、栏目列表、全任务状态。
3. 已完成配置：栏目查找与原四条筛选；未手机实测。
4. 已完成配置：逐屏While、同屏候选、同名封面XPath、MISMATCH记录、MATCH退出逐屏及末屏section_finished=True。
5. 已完成配置：86—98外层成功退出和最终提示；99—109保留禁用互动块。
6. 待实施：从流程开头手机实测，不孤立运行依赖phone_device/task_data的卡片。

每一步给当前行号和完整参数；每批同步当前进度，最终行表不得当作已实施流程。

## 本轮界面证据与待验证事项

- 手机元素编辑器的fx是全局变量选择入口，手输current_section会成为普通text，已纠正为从列表选择nav_section。
- 抖音搜索栏目保留hierarchy与底部HorizontalScrollView → LinearLayout → ActionBar.Tab → RelativeLayout → Button链；前四节点属性清空，末端Button仅text等于全局nav_section，id/index/index-attribute未勾选。用户单账号已校验固定图文定位，动态运行和跨手机尚未校验。
- 获取手机元素信息不能直接替代元素获取；第9行先得到nav_container，再第10行读取bounds。该XPath唯一性、bounds实际格式及计算结果待实测。
- 此版本无“IF 元素存在(手机)”卡片：第21行等待元素（超时5秒，用户明确设置），第22行普通IF比较nav_exists=True。隐藏栏目是否返回False、等待超时默认行为须在手机上验证，不能冒称已确认。
- 滑动手机屏幕界面已核对：常规在整个屏幕中/坐标，四项Python屏幕坐标；高级800毫秒、执行后延迟1秒。实际手势仅位于栏目bounds内。
- 原24的dp7/rej/-+结构、count(rej)=1和同名匹配序号仍使用已定方案，不把独立昵称/封面列表按索引配对。首轮运行需核对候选对应关系。
- 原46末尾图像“暂无更多，查看所有内容”仍为真实末尾识别，不点击它，不设置结果屏数上限，不新增重复屏判底或读取异常兜底。
- 原模块AST及18项纯函数检查是上一版已完成检查；本轮未重新执行模块测试，109行控制块配对及退出目标静态检查已完成，手机实测待执行。
- 企业适配保留最终61行ID读取槽位；随机互动保留最终100行策略槽位，本阶段不执行。
