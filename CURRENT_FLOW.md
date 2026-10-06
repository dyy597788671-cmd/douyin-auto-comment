# 当前影刀实际流程

## 2026-10-06 18:40 执行检查点

- 已完成第1—3批；第4批同屏候选循环和MATCH退出已由用户逐项确认，尚待补末屏section_finished=True。当前推算96行，1—85启用、86—96原互动块禁用；尚无完整导出复核和新流程手机实测。
- 用户已自行备份，影刀内module1已替换；不要重复备份、替换模块、捕获昵称/封面/头像。
- 原昵称IF未删除：右键菜单没有直接替换结构入口。当前50行保留昵称IF，51行候选ForEach包住原核验动作，75结束候选循环、76结束昵称IF。只增加和移动外层指令，原动作复用。
- 45设置section_finished=False；46 While条件Python `(not section_finished) and author_check_result != "MATCH"` 等于True；47读取已验证搜索结果作者昵称，48打印栏目、目标、本屏昵称，49创建candidate_numbers。
- 52调用build_author_cover_xpath，参数expected_author=task_data["expected_author"]、occurrence=current_candidate_number，返回字符串candidate_xpath；53原获取元素对象XPath改用candidate_xpath → mobile_element_result；54原点击复用。
- 65 IF MATCH，66退出51候选循环；68 IF MISMATCH，69 saw_id_mismatch=True，70返回结果；71结束MISMATCH。72 IF UNCERTAIN、73 Raise、74 End IF原样保留。
- 77 IF MATCH、78退出46 While、79 End IF。当前80为原末尾图像IF，81仍是原退出循环，82 End IF，83原上滑，84结束While，85结束外层栏目ForEach。
- 下一步：在当前80末尾图像IF内、81退出循环之前插入布尔设置section_finished=True。随后在While结束与外层栏目循环结束之间添加MATCH判断退出栏目循环，最后添加最终日志。
- 完整目标改为109行（实现修订FINAL-3）：保留原昵称IF和End IF两条，比FINAL-2的107行增加2条；业务规则不变，最终98条启用、99—109互动禁用。当前不是最终109行，不能用最终行号指挥后续。
- Python中的目标昵称直接使用已有task_data["expected_author"]，避免把全局变量名当普通局部变量；nav_section仍由第16行通过fx选择全局变量赋值并绑定元素text。
- 21等待超时保持用户指定5秒；28/30滑动800毫秒、执行后延迟1秒。新导航、等待超时返回、XPath候选对应关系及跨手机定位待实测，不得写已经跑通。
- ID读取失败自然停止；ID不同继续候选、屏和栏目，全部查完无MATCH提示“抖音号不同”；企业和互动本阶段不接入。

## 当前96行（按用户逐次确认推算）

| 当前行 | 影刀指令 | 配置与输出 | 来源 | 状态 |
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
| 81 | 退出循环 | 退出46行逐屏循环 | 原47 | 启用 |
| 82 | End IF | 结束80行 | 原48 | 启用 |
| 83 | 滑动手机屏幕 | 向上滑动结果列表；保留原49参数；不滑顶部导航 | 原49 | 启用 |
| 84 | 循环结束标记 | 结束46行逐屏循环 | 原50 | 启用 |
| 85 | 循环结束标记 | 结束15行栏目循环；只有类型栏目到底未匹配才进入综合 | 新增 | 启用 |
| 86 | IF 条件 | author_check_result 等于"MATCH"；整个后续互动块暂禁用 | 原51 | 禁用 |
| 87 | 调用模块 | module1.prepare_interactions(task_data) → interaction_plan；本阶段禁用 | 原52 | 禁用 |
| 88 | 设置变量 | executed_actions = []；本阶段禁用 | 原53 | 禁用 |
| 89 | ForEach列表循环 | interaction_plan["execution_order"] → current_action；本阶段禁用，恢复时核实实际键名 | 原54 | 禁用 |
| 90 | IF 条件 | current_action 等于"Like"；本阶段禁用 | 原55 | 禁用 |
| 91 | IF 条件 | interaction_plan["content_type"] 等于"视频"；本阶段禁用 | 原56 | 禁用 |
| 92 | 获取手机元素信息 | 视频——点赞按钮；原属性参数 → like_state_raw；本阶段禁用 | 原57 | 禁用 |
| 93 | End IF | 结束91行；本阶段禁用 | 原58 | 禁用 |
| 94 | End IF | 结束90行；本阶段禁用 | 原59 | 禁用 |
| 95 | 循环结束标记 | 结束89行；本阶段禁用 | 原60 | 禁用 |
| 96 | End IF | 结束86行；本阶段禁用 | 原61 | 禁用 |

## 原61行基线（历史，禁止当成当前行号）

# 当前影刀流程基线

时间：2026-10-06。用户当前主流程为61行；尚未在用户电脑修改。以下为截图逐行转录，涉及长表达式以本文件后半部分的用户补充为准。

| 原行号 | 操作 | 截图中可确认内容 |
|---|---|---|
| 1 | 调用模块 | module1.read_task，返回 task_data |
| 2 | 设置变量 | target_author = task_data["expected_author"]，字符串 |
| 3 | 连接手机 | Appium模式，运行时手动选择，返回 phone_device |
| 4 | 打开手机APP | phone_device；com.ss.android.ugc.aweme；激活到屏幕 |
| 5 | 等待 | 3—10秒 |
| 6 | 点击元素(手机) | 抖音搜索入口；单击中心 |
| 7 | 输入文本(手机) | phone_device；抖音搜索输入框；task_data["keyword"] |
| 8 | 点击元素(手机) | 搜索按钮；单击中心 |
| 9 | IF | task_data["search_section"] 等于 图文 |
| 10 | 点击元素(手机) | 搜索分区_图文；在9内 |
| 11 | End IF | 结束9 |
| 12 | IF | task_data["search_section"] 等于 视频 |
| 13 | 点击元素(手机) | 搜索分区_视频；在12内 |
| 14 | End IF | 结束12 |
| 15 | 点击元素(手机) | 抖音筛选入口 |
| 16 | 点击屏幕(手机) | phone_device；通过图像匹配取得坐标；具体图像及设置未展示 |
| 17 | 点击屏幕(手机) | 同上，具体目标未展示 |
| 18 | 点击屏幕(手机) | 同上，具体目标未展示 |
| 19 | 设置变量 | author_check_result = NOT_FOUND，字符串 |
| 20 | While条件循环 | True 等于 True |
| 21 | 获取相似元素列表(手机) | phone_device；搜索结果作者昵称；获取文本；返回 author_name_list；在20内 |
| 22 | 打印日志 | 信息；目标昵称和本屏读取昵称；长表达式在截图中被截断；在20内 |
| 23 | IF | 表达式以 task_data["expected_author"] in… 开头，比较 True；完整表达式未展示；在20内 |
| 24 | 获取元素对象(手机) | phone_device；XPath以 //*[@resource-id='com.ss.andr… 开头；返回 mobile_element_result；完整XPath未展示；在23内 |
| 25 | 点击元素(手机) | mobile_element_result；单击中心；在23内 |
| 26 | 设置变量 | is_tuwen，布尔；表达式 task_data["content_type"] == "图… 被截断；在23内 |
| 27 | IF | is_tuwen 等于 True；在23内 |
| 28 | 点击元素(手机) | 图文作者头像；在27真分支 |
| 29 | Else | 对应27 |
| 30 | 点击元素(手机) | 视频作者头像；在27假分支 |
| 31 | End IF | 结束27 |
| 32 | 获取手机元素信息 | 文本；抖音主页_账号；返回 profile_douyin_id_raw；在23内 |
| 33 | 获取手机元素信息 | 文本；主页_作者昵称；返回 profile_author_name_raw；在23内 |
| 34 | 调用模块 | module1.verify_author；传 task_data、profile_douyin_id_raw、profile_author_name_raw；返回设置未展示；在23内 |
| 35 | 点击按键 | phone_device；后退；在23内 |
| 36 | IF | author_check_result 等于 MATCH；在23内 |
| 37 | 退出循环 | 退出当前循环；在36内 |
| 38 | End IF | 结束36 |
| 39 | IF | author_check_result 等于 MISMATCH；在23内 |
| 40 | 点击按键 | phone_device；后退；在39内 |
| 41 | End IF | 结束39 |
| 42 | IF | author_check_result 等于 UNCERTAIN；在23内 |
| 43 | Raise | 作者抖音号核验不确定，请检查任务表中的抖音号及主页读取结果；在42内 |
| 44 | End IF | 结束42 |
| 45 | End IF | 结束23 |
| 46 | IF 图像存在(手机) | phone_device；目标图像显示名为“图像”；实际图像未展示；在20内 |
| 47 | 退出循环 | 退出当前循环；在46内 |
| 48 | End IF | 结束46 |
| 49 | 滑动手机屏幕 | phone_device；向上滑动；在20内 |
| 50 | 循环结束标记 | 结束20 |
| 51 | IF | author_check_result 等于 MATCH |
| 52 | 调用模块 | module1.prepare_interactions；task_data；返回 interaction_plan；在51内 |
| 53 | 设置变量 | executed_actions = []，列表；在51内 |
| 54 | ForEach列表循环 | interaction_plan["execution_orde… 被截断；循环项 current_action；在51内 |
| 55 | IF | current_action 等于 Like；在54内 |
| 56 | IF | interaction_plan["content_type"] 等于 视频；在55内 |
| 57 | 获取手机元素信息 | 获取属性；视频——点赞按钮（图中显示）；返回 like_state_raw；具体属性未展示；在56内 |
| 58 | End IF | 结束56 |
| 59 | End IF | 结束55 |
| 60 | 循环结束标记 | 结束54 |
| 61 | End IF | 结束51 |

## 用户补充的完整配置

- 原16：最新发布，图像识别。
- 原17：一天内，图像识别。
- 原18：红色底框“查看结果”，图像识别。
- 原46：“暂无更多，查看所有内容”，图像识别；作为展示结束标记，不点击它。
- 原23：Python `task_data["expected_author"] in author_name_list`，比较True。
- 原26：本次定稿以 `task_data["content_type"] == "图文"` 写入is_tuwen。
- 原34：module1.verify_author；输入task_data、profile_douyin_id_raw、profile_author_name_raw；返回任意类型；输出author_check_result。已核对正确。
- 原54的执行列表键在截图中被截断，定稿互动块暂禁用，未来恢复时核实；本阶段无需改其业务。
- 当前module1完整代码由用户上传文本提供，对应module1.baseline.py；原逻辑留存，新的两个纯计算函数位于module1.py末尾。

原24行完整表达式：

```python
"//*[@resource-id='com.ss.android.ugc.aweme:id/dp7'][count(.//*[@resource-id='com.ss.android.ugc.aweme:id/rej'])=1 and .//*[@resource-id='com.ss.android.ugc.aweme:id/-+' and @text=concat(''," + ", \"'\", ".join("'" + part + "'" for part in task_data["expected_author"].split("'")) + ")]]//*[@resource-id='com.ss.android.ugc.aweme:id/rej']"
```

导航实据：初始截图可见综合、团购、视频、直播、用户；图文隐藏在右侧。横向滚动后可见用户、图文、商品、音乐、话题、小程序。用户已确认不同设备栏目顺序不同，不能按固定序号或某机型坐标定位。

![原1—61行拼接图](CURRENT_FLOW.png)
