# 打卡任务、日历、AI 规划 — 端到端修复计划

## 诊断结论

通过后端日志和全链路代码审查，定位到 3 个缺陷。

---

### Bug 1：日历 `/calendar/month` 500 NameError

**根因**：`calendar_router.py` 第 116 行，上次编辑时替换掉了 `suggested_tasks_map = {}` 初始化语句，导致第 130 行 `if cur not in suggested_tasks_map` 抛 NameError。

**日志证据**：
```
NameError: name 'suggested_tasks_map' is not defined
  File "...calendar_router.py", line 130, in get_month_calendar
```

**修复**：在第 116 行注释后补回 `suggested_tasks_map = {}`。

---

### Bug 2：AI 规划 DeepSeek JSON 解析三次全失败

**根因**：DeepSeek API 能连通、Key 有效，但返回的 JSON 存在语法错误（`Expecting ',' delimiter: line 433 column 6`），三次重试全部解析失败，最终抛出 500。

**日志证据**：
```
[AI] Parse error (attempt 1/3): Expecting ',' delimiter: line 433 column 6 (char 11755)
[AI] Parse error (attempt 2/3): Expecting ',' delimiter: line 473 column 6 (char 12082)
[AI] Parse error (attempt 3/3): Expecting ',' delimiter: line 483 column 6 (char 12304)
POST /ai/generate-plan HTTP/1.1 500 Internal Server Error
```

**分析**：DeepSeek 在某些情况下输出超长内容时，JSON 中会出现不规范的逗号缺失。当前对策不足——仅去掉 markdown 包裹、每次降低 temperature 重试，但 JSON 本体语法错误无法靠降低 temperature 修复。

**修复方案**：
1. 添加 `response_format: {"type": "json_object"}` 强制 DeepSeek 输出合法 JSON
2. 增加 `max_tokens` 到 8192，防止内容截断导致 JSON 不完整
3. 增加 JSON 容错解析：当 `json.loads` 失败时，尝试用正则从文本中提取 `task_name`/`scheduled_date` 等关键字段做降级解析

---

### 端到端数据流对齐验证

经全链路审查，以下前后端字段映射已对齐（之前的修复已覆盖）：

| 数据流 | 前端字段 | 后端字段 | 状态 |
|--------|---------|---------|------|
| 任务创建 | `name, start_date, subject, suggested_duration, task_type, repeat_days` → POST /tasks/batch | `TaskCreate` | 已对齐 |
| 日历月视图 | `dayData.status` → CSS class | `CalendarDate.status` | 已对齐 |
| 日历日期弹层 | `dayData.suggested_tasks_preview[]` | `CalendarDate.suggested_tasks_preview: List[str]` | 已对齐 |
| 日历日期弹层 | `dayData.checkin_count` | `CalendarDate.checkin_count: int` | 已对齐 |
| 今日任务 | `todayData.tasks[].name` | `TodayTaskItem.name` | 已对齐 |
| 明日推荐 | `tomorrowData.recommended_tasks[].task_name` | `TomorrowRecommendedTask.task_name` | 已对齐 |
| 首页统计 | `stats.current_streak, weekly_rate, monthly_rate` | `StatsResponse` | 已对齐 |
| 打卡查询 | `checkinsRes[].task_id` | `CheckinOut.task_id` | 已对齐 |
| AI 计划日期 | `aiPlanData[].scheduled_date` → confirmPlan | `AIPlanTask.scheduled_date` | 已对齐 |

**建议的任务数据流**（用于测试验证）：
```
规划页输入目标 → AI 生成计划(带日期) → 确认创建 → POST /tasks/batch(各自 start_date)
→ 首页 GET /tasks/?status=active(按日期过滤) → 点击打卡 POST /checkins/{task_id}
→ 日历 GET /calendar/month(suggested_tasks_map 展开) → 格子颜色(status)
→ 日历点击日期(弹层显示 suggested_tasks_preview)
→ 统计 GET /stats/(current_streak, weekly_rate, monthly_rate 更新)
```

---

## 修改文件清单

### 1. `backend/routers/calendar_router.py`
- 在第 116 行后补回 `suggested_tasks_map = {}`

### 2. `backend/routers/ai_router.py`
- 在 `payload` 中添加 `"response_format": {"type": "json_object"}`
- `max_tokens` 从 4096 改为 8192
- 增强 `parse_ai_response` 容错：`json.loads` 失败后尝试从文本中正则提取 task_name 和 scheduled_date 做降级解析

---

## 验证步骤
1. 重启后端，确认无异常
2. 打开小程序 → 日历 Tab → 不弹"请求失败"
3. 规划页 → 输入目标 → AI 规划 → 应生成带日期的计划
4. 确认创建计划 → 首页看到任务 → 日历各格子按日期显示对应颜色
5. 首页打卡 → 日历刷新 → 今日格子变赤陶色（已打卡）
