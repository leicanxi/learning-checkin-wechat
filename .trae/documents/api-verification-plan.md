# 前后端 API 对接验证计划

## 一、现状总览

| | 数量 |
|---|---|
| 后端端点 | 37 个 |
| 前端调用 | 17 次（对应 12 个路径） |
| 完全匹配 | 6 个 |
| 需要修复 | 6 个 |

---

## 二、匹配成功的接口（无需改动）

| 前端调用 | 后端端点 | 
|---|---|
| `GET /calendar/month?year=&month=` | `GET /calendar/month` |
| `GET /calendar/today` | `GET /calendar/today` |
| `GET /calendar/tomorrow` | `GET /calendar/tomorrow` |
| `GET /settings/reminder` | `GET /settings/reminder` |
| `GET /groups/my` | `GET /groups/my` |
| `POST /auth/wechat-login` | `POST /auth/wechat-login` |

---

## 三、需要修复的接口（6 个）

### 3.1 路径不一致

| 问题 | 前端调用 | 后端实际 |
|---|---|---|
| 统计路径 | `GET /stats/summary` | `GET /stats/` |
| 用户更新路径 | `PUT /users/me` | `PUT /auth/me` |
| 取消打卡 | `POST /checkins/:id/undo` | `DELETE /checkins/{checkin_id}` |
| 创建打卡 | `POST /checkins` | `POST /checkins/` |

**修复方式：统一改前端** `utils/api.js` 调用路径或各页面 JS 中的 URL。

### 3.2 参数名不一致

| 问题 | 前端发送 | 后端期望 |
|---|---|---|
| 排名维度 | `?dimension=group` | `?scope=group` |

**修复方式：** 修改 `stats.js` 中 `get('/ranking/me', { dimension: ... })` → `{ scope: ... }`

### 3.3 请求体字段不匹配

| 接口 | 前端发送字段 | 后端期望字段 |
|---|---|---|
| `POST /ai/generate-plan` | `{ learning_mode, material_text }` | `{ content, mode?, target_days? }` |
| `POST /tasks/batch` | `{ tasks: [{ name, subject, duration_minutes, task_type, learning_mode, material_text }] }` | `{ tasks: [{ name, description?, subject?, suggested_duration?, task_type?, repeat_days?, difficulty?, start_date, end_date? }] }` |

**修复方式：**
- AI 规划：前端 `learning_mode` → 后端 `mode`，前端 `material_text` → 后端 `content`
- 批量任务：前端所有字段映射到后端 `TaskCreate` schema，`start_date` 默认填当天

---

## 四、需要用户验证的功能（需在小程序真机/模拟器操作）

### 4.1 登录流程
1. 打开小程序 → 切换到"设置"页
2. 点击"点击头像登录" → 微信授权弹窗
3. 确认后观察是否显示"登录成功" Toast
4. 验证头像和昵称是否正确显示
5. 关闭小程序再打开，验证 Token 持久化（无需重新登录）

### 4.2 首页打卡
1. 确认首页是否显示"今日任务"列表
2. 点击任务复选框 → 观察"打卡成功/失败"Toast
3. 连续打卡数、本周/本月打卡率是否更新
4. 再点击已打勾的任务 → 观察"已取消打卡"Toast

### 4.3 日历展示
1. 切换到日历页 → 月份是否正确显示
2. 日期格子颜色是否正确（已完成/未打卡/休息日/今日）
3. 点击不同状态的日期 → 弹层描述是否正确
4. 今日/明日推荐卡片是否有内容

### 4.4 AI 规划
1. 切换到规划页 → 选择学习模式
2. 输入学习材料描述 → 点击"AI 规划"
3. 观察是否生成计划列表
4. 点击"确认创建计划" → 是否跳转首页并显示新任务

### 4.5 统计页
1. 切换到统计页 → 趋势图是否渲染（折线/柱状）
2. 环形进度、深色完成卡片是否显示数据
3. 切换"周/月/年" → 数据是否变化
4. 排名 Hero 区是否显示排名区间
5. 切换"小组/全局" → 排名是否变化
6. 徽章墙展开/收起是否正常

### 4.6 设置页
1. 每日打卡提醒开关切换
2. 任务到期通知开关切换
3. 编辑学习目标 → 确认保存后显示是否正确
4. 退出登录 → 确认回到未登录状态

---

## 五、修复步骤

### Step 1：修正前端 API 路径 `miniapp/utils/api.js` 及各页面 JS

- `pages/home/home.js`：`/stats/summary` → `/stats/`，`/checkins/today` → `/checkins/?start_date={today}&end_date={today}`（或后端新增 today 端点）
- `pages/stats/stats.js`：`/stats/summary` → `/stats/`，`dimension` → `scope`
- `pages/planner/planner.js`：AI 请求体字段映射，`/tasks/batch` 请求体字段映射
- `pages/settings/settings.js`：`/users/me` → `/auth/me`

### Step 2：对齐请求体字段

- AI 规划：`learning_mode` → `mode`、`material_text` → `content`
- 批量任务：添加 `suggested_duration`、`start_date`、`repeat_days` 等必填字段

### Step 3：处理取消打卡

- `POST /checkins/:id/undo` → `DELETE /checkins/{checkin_id}`

### Step 4：用户逐页验证

按第四章列出场景操作，反馈结果。

---

## 六、后端正缺失端点（可选，后续补充）

| 前端需要的端点 | 说明 | 临时方案 |
|---|---|---|
| `GET /tasks/today` | 返回今日任务 | 后端暂无此端点，需新增或用 `GET /tasks/?status=active` 过滤 |
| `GET /checkins/today` | 返回今日打卡记录 | 后端用 `GET /checkins/?start_date=&end_date=` 代替 |
