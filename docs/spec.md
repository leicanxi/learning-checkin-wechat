# 学习打卡追踪器 - 技术设计文档

> **关联文档**：[PRD.md](PRD.md) | [tasks.md](tasks.md)  
> **文档版本**：v2.0  
> **最后更新**：2026-07-03

---

## 一、技术栈选择

### 1.1 前端技术栈

| 技术 | 版本 | 选择理由 |
| --- | --- | --- |
| **框架** | Taro 3.x | 支持多端开发（微信小程序/H5/APP），Vue3语法，与微信小程序原生能力深度集成 |
| **语言** | TypeScript | 类型安全，提升代码质量和可维护性 |
| **UI组件** | Taro UI | 专为Taro设计的组件库，适配多端 |
| **状态管理** | Pinia | Vue官方推荐，轻量级状态管理 |
| **图表库** | ECharts | 支持小程序端，功能强大的图表展示 |

### 1.2 后端技术栈

| 技术 | 版本 | 选择理由 |
| --- | --- | --- |
| **框架** | FastAPI 0.100+ | 高性能异步框架，自动生成API文档，适合AI集成 |
| **语言** | Python 3.11+ | 丰富的数据分析库，适合规律性计算和AI调用 |
| **数据库** | SQLite | 轻量级，无需额外部署，适合小型应用及个人测试号开发；后续可迁移至PostgreSQL |
| **ORM** | SQLAlchemy 2.0 | 强大的ORM工具，支持SQLite |
| **认证** | JWT | 无状态认证，适合前后端分离架构 |
| **AI API** | DeepSeek | 支持知识点拆解和学习规划 |
| **语音识别** | 腾讯云 ASR | 微信生态兼容好，延迟低，中文识别准确率高 |
| **PDF 生成** | reportlab | 纯 Python，适合程序化生成统计图表和表格，无需外部渲染引擎 |

### 1.3 部署方案

| 组件 | 开发环境（测试号） | 生产环境（正式号） |
| --- | --- | --- |
| 前端 | Taro dev + 微信开发者工具 + 测试号 AppID | 正式号 AppID + 代码上传审核 |
| 后端 | `uvicorn main:app --reload` 本地运行 | 腾讯云 Serverless / 轻量云服务器 + HTTPS |
| 数据库 | SQLite 本地文件 | SQLite（后续可迁移至 PostgreSQL） |
| AI API | 环境变量 `DEEPSEEK_API_KEY`（开发 Key） | 环境变量（生产 Key） |

### 1.4 个人测试号开发约束

| 约束项 | 影响 | 应对方案 |
| --- | --- | --- |
| 无模板消息 | 无法使用 `wx.requestSubscribeMessage` | 小程序内 `wx.showModal` 本地弹窗；代码预留正式号模板消息接口 |
| 无手机号授权 | 无法获取微信绑定手机号 | 不依赖手机号，仅通过 `openid` 标识用户 |
| 请求域名不校验 | 开发阶段可直接调用本地服务 | 代码不硬编码域名，全部走 `config.ts` |
| 最多 15 体验者 | 无法大规模分发 | 满足内部测试；正式号无此限制 |
| 无法发布上线 | 仅开发调试 | 代码不依赖测试号特有 API |

---

## 二、认证流程

### 2.1 主流程：微信小程序登录

```
用户打开小程序
    ↓
wx.login() 获取临时 code
    ↓
前端 POST /auth/wechat-login  { code }
    ↓
后端调用微信 code2Session → 获取 openid
    ↓
查找 users 表（WHERE openid = ?），不存在则自动注册
    ↓
生成 JWT token（payload: { user_id, openid, role }）
    ↓
返回 { access_token, token_type, user }
    ↓
前端存储 token → 后续请求在 Header 中携带 Authorization: Bearer <token>
```

### 2.2 备选流程：邮箱密码登录（开发调试用）

> 仅用于开发阶段后端 API 调试，不暴露于小程序前端入口。

```
POST /auth/login { email, password }
    → 后端 bcrypt 校验密码
    → 返回 JWT token
```

### 2.3 鉴权中间件

```python
# get_current_user: 所有需要登录的接口依赖此函数
# → 从 Header 中提取 Bearer token → 解析 JWT → 返回 user 对象

# require_admin: 管理员接口依赖此函数（预留，MVP 阶段不挂载到任何路由）
def require_admin(user = Depends(get_current_user)):
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
```

---

## 三、数据库设计

### 3.1 数据库表结构

#### 3.1.1 users（用户表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 用户ID |
| openid | VARCHAR(64) | UNIQUE | 微信OpenID（wx.login获取） |
| nickname | VARCHAR(100) | DEFAULT '' | 用户昵称 |
| avatar | VARCHAR(500) | DEFAULT '' | 用户头像URL |
| learning_goal | VARCHAR(200) | DEFAULT '' | 学习目标描述（设置页可编辑） |
| role | VARCHAR(10) | DEFAULT 'user' | 角色：`user`（普通用户）/ `admin`（系统管理员，DB 手动设置）；小组管理员通过 groups.creator_id 判断 |
| email | VARCHAR(100) | UNIQUE, NULLABLE | 邮箱（开发调试备选登录） |
| password_hash | VARCHAR(255) | NULLABLE | 密码哈希 |
| timezone | VARCHAR(50) | DEFAULT 'Asia/Shanghai' | 时区 |
| reminder_enabled | BOOLEAN | DEFAULT FALSE | 每日打卡提醒开关 |
| reminder_time | TIME | DEFAULT '21:00:00' | 提醒时间 |
| task_expire_notify | BOOLEAN | DEFAULT TRUE | 任务到期通知开关 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

#### 3.1.2 tasks（打卡任务表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 任务ID |
| user_id | INTEGER | FOREIGN KEY → users(id) | 用户ID |
| name | VARCHAR(50) | NOT NULL | 任务名称 |
| description | VARCHAR(200) | DEFAULT '' | 任务描述 |
| subject | VARCHAR(50) | DEFAULT '' | 科目标签（如"英语""数学"），统计页科目分布数据源 |
| suggested_duration | INTEGER | DEFAULT 25 | 建议时长（分钟） |
| task_type | VARCHAR(20) | DEFAULT 'main' | 任务类型：`main`（主任务，墨色标签）/ `light`（轻量，鼠尾草色标签）/ `review`（AI推荐复习，赤陶色标签） |
| repeat_days | INTEGER | DEFAULT 127 | 打卡周期位掩码：bit0=周一...bit6=周日；127=每天，0=不重复 |
| difficulty | VARCHAR(10) | DEFAULT 'medium' | 难度：`low` / `medium` / `high` |
| start_date | DATE | NOT NULL | 开始日期 |
| end_date | DATE | NULLABLE | 结束日期 |
| status | VARCHAR(20) | DEFAULT 'active' | 状态：active / completed / expired / deleted |
| is_ai_generated | BOOLEAN | DEFAULT FALSE | 是否AI生成 |
| is_review_task | BOOLEAN | DEFAULT FALSE | 是否遗忘曲线生成的复习任务 |
| parent_task_id | INTEGER | NULLABLE, FOREIGN KEY → tasks(id) | 复习任务关联的原任务ID |
| ai_review_intervals | TEXT | NULLABLE | AI推荐复习间隔（JSON数组: [1,2,4,7,15]） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

#### 3.1.3 checkins（打卡记录表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 记录ID |
| user_id | INTEGER | FOREIGN KEY → users(id) | 用户ID |
| task_id | INTEGER | FOREIGN KEY → tasks(id) | 任务ID |
| subject | VARCHAR(50) | DEFAULT '' | 打卡时的科目标签（冗余，方便统计聚合） |
| checkin_time | DATETIME | NOT NULL | 打卡时间 |
| is_review | BOOLEAN | DEFAULT FALSE | 是否复习打卡 |
| review_round | INTEGER | DEFAULT 0 | 复习轮次（0=新学，1-5=第n次复习） |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### 3.1.4 groups（小组表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 小组ID |
| name | VARCHAR(100) | NOT NULL | 小组名称 |
| description | VARCHAR(500) | DEFAULT '' | 小组描述 |
| invite_code | VARCHAR(20) | UNIQUE | 邀请码，用户凭此加入 |
| creator_id | INTEGER | FOREIGN KEY → users(id) | 创建者ID |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### 3.1.5 user_groups（用户小组关联表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| user_id | INTEGER | FOREIGN KEY → users(id) | 用户ID |
| group_id | INTEGER | FOREIGN KEY → groups(id) | 小组ID |
| joined_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 加入时间 |

#### 3.1.6 badges（徽章表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 徽章ID |
| name | VARCHAR(50) | NOT NULL | 徽章名称（共10个：规律达人/习惯养成者/进步之星/七日连续/英语坚持/错题复盘/早起学习/晚间专注/小组贡献/新计划创建） |
| description | VARCHAR(200) | DEFAULT '' | 徽章描述 |
| type | VARCHAR(20) | NOT NULL | 类型：regularity / progress / achievement |
| threshold | REAL | NULLABLE | 获得阈值（规律性得分等） |
| icon_css | VARCHAR(500) | DEFAULT '' | 徽章图标CSS样式标识 |

#### 3.1.7 user_badges（用户徽章关联表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| user_id | INTEGER | FOREIGN KEY → users(id) | 用户ID |
| badge_id | INTEGER | FOREIGN KEY → badges(id) | 徽章ID |
| earned_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 获得时间 |

### 3.2 数据关系图

```
users  1 ───── *  tasks
  │              │
  │              * ───── *  checkins
  │
  1 ───── *  user_groups  * ───── 1  groups
  │
  1 ───── *  user_badges   * ───── 1  badges
```

### 3.3 位掩码说明（repeat_days）

| 位 | 值 | 含义 |
| --- | --- | --- |
| bit0 | 1 | 周一 |
| bit1 | 2 | 周二 |
| bit2 | 4 | 周三 |
| bit3 | 8 | 周四 |
| bit4 | 16 | 周五 |
| bit5 | 32 | 周六 |
| bit6 | 64 | 周日 |

127 = 1+2+4+8+16+32+64 = 每天

---

## 四、API接口设计

### 4.0 全局约定

- 除登录/注册接口外，所有接口需携带 `Authorization: Bearer <jwt_token>`
- 响应格式: `{ "data": {...}, "message": "string", "code": 200 }`
- 错误格式: `{ "detail": "error message" }` + HTTP 4xx/5xx

### 4.1 用户认证

| 接口 | 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- | --- |
| **微信登录** | POST | /auth/wechat-login | 无 | 小程序主入口，接收wx.login()的code → 返回JWT |
| 邮箱注册 | POST | /auth/register | 无 | 开发调试备选 |
| 邮箱登录 | POST | /auth/login | 无 | 开发调试备选 |
| 获取用户信息 | GET | /auth/me | Bearer | 获取当前用户完整信息 |
| 更新用户信息 | PUT | /auth/me | Bearer | 更新昵称、学习目标、头像 |
| 上传头像 | POST | /auth/avatar | Bearer | 上传用户头像（≤2MB） |

#### 请求/响应示例

**POST /auth/wechat-login**
```json
// Request
{
  "code": "string (必填, wx.login()返回的临时code)"
}

// Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "openid": "oABC123xyz...",
    "nickname": "学习达人",
    "avatar": "",
    "learning_goal": "",
    "created_at": "2026-01-01T00:00:00"
  }
}
```

**POST /auth/register**
```json
// Request
{
  "nickname": "string (必填, 1-100字符)",
  "email": "string (必填, 邮箱格式)",
  "password": "string (必填, 6-50字符)"
}
```

**PUT /auth/me**
```json
// Request
{
  "nickname": "string (可选)",
  "learning_goal": "string (可选, 0-200字符)",
  "avatar": "string (可选, URL)"
}
```

### 4.2 任务管理

| 接口 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 创建任务 | POST | /tasks/ | 创建单个打卡任务 |
| 批量创建任务 | POST | /tasks/batch | AI规划页确认后批量创建 |
| 获取任务列表 | GET | /tasks/ | 获取用户任务列表（支持 ?status=active） |
| 获取任务详情 | GET | /tasks/{id} | 获取任务详情 |
| 更新任务 | PUT | /tasks/{id} | 更新任务 |
| 删除任务 | DELETE | /tasks/{id} | 软删除（status='deleted'），保留历史打卡记录 |

#### 请求/响应示例

**POST /tasks/**
```json
// Request
{
  "name": "string (必填, 1-50字符)",
  "subject": "string (可选, 科目标签)",
  "suggested_duration": "integer (可选, 分钟, 默认25)",
  "task_type": "string (可选, 'main'|'light'|'review', 默认'main')",
  "repeat_days": "integer (可选, 位掩码, 默认127=每天)",
  "difficulty": "string (可选, 'low'|'medium'|'high', 默认'medium')",
  "start_date": "string (必填, YYYY-MM-DD)",
  "end_date": "string (可选, YYYY-MM-DD)"
}

// Response
{
  "id": 1,
  "name": "背单词30分钟",
  "subject": "英语",
  "suggested_duration": 30,
  "task_type": "main",
  "repeat_days": 127,
  "difficulty": "medium",
  "start_date": "2026-01-01",
  "end_date": null,
  "status": "active",
  "is_ai_generated": false,
  "is_review_task": false,
  "created_at": "2026-01-01T10:00:00"
}
```

**POST /tasks/batch**
```json
// Request
{
  "tasks": [
    {
      "name": "string (必填)",
      "subject": "string (可选)",
      "suggested_duration": "integer (可选)",
      "task_type": "string (可选)",
      "repeat_days": "integer (可选)",
      "difficulty": "string (可选)",
      "start_date": "string (必填, YYYY-MM-DD)"
    }
  ]
}

// Response
{
  "created_count": 5,
  "tasks": [ { "id": 1, "name": "..." }, ... ]
}
```

### 4.3 打卡记录

| 接口 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 打卡 | POST | /checkins/ | 完成打卡（支持每日多次） |
| 补打卡 | POST | /checkins/backfill | 补打卡最近7天 |
| 获取打卡记录 | GET | /checkins/ | 获取打卡记录列表 |
| 获取打卡详情 | GET | /checkins/{id} | 获取打卡详情 |
| 更新打卡记录 | PUT | /checkins/{id} | 更新打卡记录 |
| 删除打卡记录 | DELETE | /checkins/{id} | 删除打卡记录 |

#### 请求示例

**POST /checkins/**
```json
{
  "task_id": "integer (必填)",
  "checkin_time": "string (可选, ISO datetime, 默认当前时间)",
  "is_review": "boolean (可选, 默认false)"
}
```

**POST /checkins/backfill**
```json
{
  "task_id": "integer (必填)",
  "checkin_date": "string (必填, YYYY-MM-DD, 必须是最近7天内)"
}
// 超过7天 → 400 { "detail": "补打卡不可超过7天" }
```

### 4.4 AI服务

| 接口 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 上传学习材料 | POST | /ai/upload-material | 上传学习材料文件（图片/文档），供AI分析 |
| AI分析学习材料 | POST | /ai/analyze | 分析学习材料并拆解任务 |
| AI生成学习计划 | POST | /ai/generate-plan | AI 将学习材料拆解为子任务，为每个子任务分配具体执行日期 |
| AI预估进度 | GET | /ai/progress | 获取AI预估学习进度 |

#### 模式推断逻辑

后端收到请求后，按以下优先级确定学习模式：

```
1. 前端显式传入 mode 参数 → 直接使用
2. mode 为空 / null → 后端对 content 做 NLP 关键词匹配：
   - 含「冲刺」「倒计时」「仅剩X天」「考试」「deadline」→ 推断为 "exam"
   - 含「长期」「积累」「每天一点点」「坚持」「日常」→ 推断为 "daily"
   - 含「技能」「入门到精通」「进阶」「掌握」→ 推断为 "skill"
   - 含「错题」「复盘」「回顾」「查漏补缺」→ 推断为 "review"
   - 无匹配 → 默认 "free"
3. mode="free" 或推断结果→ AI 自行判断最佳排期方式
```

#### 请求/响应示例

**POST /ai/generate-plan**（规划页核心接口）
```json
// Request
{
  "content": "string (必填, 学习材料或目标描述，可含时限等提示词)",
  "mode": "string (可选, 'exam'|'daily'|'skill'|'review'|'free'；为空则从 content 推断，均无法推断默认 'free')",
  "target_days": "integer (可选, 用户期望的总天数，如 30；为空则由 AI 根据内容量自动估算)"
}

// mode 枚举映射及 AI Prompt 策略:
// 'exam'  → 考试冲刺：短时间密集排期，每天可能多个子任务，严格在 target_days 内完成
// 'daily' → 日常积累：长期多次反复，不一定每天排任务，AI 根据内容量决定频率（隔天/每周三次等），注重复习穿插
// 'skill' → 技能进修：阶段性递进，先基础后进阶，任务难度逐步提升
// 'review'→ 错题复盘：以间隔拉长的节奏安排（1/2/4/7/15天），与遗忘曲线吻合
// 'free'  → 自由模式：AI 综合分析后自主决定最佳排期策略

// Response
{
  "mode": "exam",
  "mode_inferred": false,
  "total_days": 30,
  "summary": "该计划将在30天内完成高考数学全面复习，每天1-3个子任务，覆盖函数、几何、概率等全部模块。",
  "plan": [
    {
      "task_name": "函数基础复习",
      "scheduled_date": "2026-03-15",
      "day_number": 1,
      "subject": "数学",
      "suggested_duration": 45,
      "difficulty": "medium",
      "knowledge_tags": ["函数", "基础"],
      "review_round": 0
    },
    {
      "task_name": "三角函数专题",
      "scheduled_date": "2026-03-16",
      "day_number": 2,
      "subject": "数学",
      "suggested_duration": 60,
      "difficulty": "medium",
      "knowledge_tags": ["三角函数", "公式"],
      "review_round": 0
    },
    {
      "task_name": "几何证明训练",
      "scheduled_date": "2026-03-17",
      "day_number": 3,
      "subject": "数学",
      "suggested_duration": 50,
      "difficulty": "high",
      "knowledge_tags": ["几何", "证明"],
      "review_round": 0
    }
  ]
}

// scheduled_date: YYYY-MM-DD，子任务应执行的日期
// day_number: 计划中的第 N 天（从1开始）
// review_round: 0=新学任务，1-5=第n轮复习（AI 自动规划复习穿插）
// mode_inferred: true=模式由后端从 content 推断得出，false=模式由前端显式传入
```

**各模式的典型 Prompt 指令（后端组装）：**

| 模式 | 核心 Prompt 指令 |
| --- | --- |
| exam | "你是一个考试冲刺规划师。用户在{target_days}天内需要完成备考。请将学习材料拆解为子任务，每天安排1-3个子任务，严格在{target_days}天内排满，每个子任务必须指定 scheduled_date。" |
| daily | "你是日常积累规划师。用户希望长期学习，请将材料拆解为子任务，不必每天排任务，合理安排频率（如隔天、每周3次），注重新学和复习交替。每个子任务必须指定 scheduled_date。" |
| skill | "你是技能进修规划师。请将学习路径分为基础→进阶→实战阶段，各阶段分配合理的子任务和日期，任务难度逐步提升。每个子任务必须指定 scheduled_date。" |
| review | "你是错题复盘规划师。请按艾宾浩斯遗忘曲线安排复盘节奏（间隔1/2/4/7/15天），每个错题集安排多轮复盘作为独立子任务。所有子任务的 review_round 固定为 0（实际复习轮次的 review_round 由系统遗忘曲线服务自动管理）。每个子任务必须指定 scheduled_date。" |
| free | "请综合分析学习材料的难度、内容量和用户描述，自主决定最佳排期策略。每个子任务必须指定 scheduled_date。" |

> task_name 去重规则：AI 生成的复习计划（review_round>0 的子任务）交由遗忘曲线（US-20/Task 17）统一触发，/ai/generate-plan 返回的 plan 中 review_round 固定为 0（AI 只规划新学任务，复习由系统自动安排）。

### 4.5 统计服务

| 接口 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 获取统计数据 | GET | /stats/ | 获取用户统计数据 |
| 获取规律性排行 | GET | /ranking/ | 获取规律性排行榜 |
| 获取用户排名 | GET | /ranking/me | 获取当前用户排名区间 |
| 获取徽章列表 | GET | /badges/ | 获取全部徽章列表 |
| 获取用户徽章 | GET | /badges/me | 获取用户已获得的徽章 |

#### 响应示例

**GET /stats/?period=week|month|year&start=&end=**
```json
{
  "current_streak": 15,
  "longest_streak": 30,
  "weekly_rate": 85.5,
  "monthly_rate": 78.3,
  "total_checkins": 247,
  "knowledge_progress": {
    "learning": 40,
    "reviewing": 30,
    "mastered": 30,
    "_source": "AI 根据用户打卡频率、复习完成率、每日平均学习时长动态计算"
  },
  "subject_distribution": [
    { "subject": "英语", "count": 85, "percentage": 42.5 },
    { "subject": "数学", "count": 60, "percentage": 30.0 },
    { "subject": "物理", "count": 55, "percentage": 27.5 }
  ],
  "checkin_trend": [
    { "date": "2026-01-01", "count": 2 },
    { "date": "2026-01-02", "count": 3 }
  ],
  "estimated_remaining_days": 12
}
```

**GET /ranking/me?scope=group|global**
```json
{
  "user_id": 1,
  "regularity_score": 92.5,
  "rank_range": "top_20",
  "rank_range_label": "前 20%",
  "rank_title": "规律达人",
  "total_participants": 150,
  "scope": "global",
  "group_id": null,
  "group_rank_range": null
}

// rank_range 枚举:
// "top_20"     → 前 20%
// "top_60"     → 20%-60%
// "bottom_40"  → 60%+
// "insufficient" → 打卡不足7次
```

### 4.6 日历服务

| 接口 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 获取日历月数据 | GET | /calendar/month?year=&month= | 返回该月每日打卡状态 + 日期详情 |
| 获取今日任务 | GET | /calendar/today | 返回今日安排的任务列表 |
| 获取明日推荐 | GET | /calendar/tomorrow | 返回AI推荐的明日任务 + 休息建议 |

#### 响应示例

**GET /calendar/month?year=2026&month=1**
```json
{
  "year": 2026,
  "month": 1,
  "monthly_completion_rate": 72.5,
  "dates": [
    {
      "date": "2026-01-01",
      "day_of_week": 4,
      "status": "checked_in",
      "checkin_count": 2,
      "is_today": false,
      "is_rest_suggested": false
    },
    {
      "date": "2026-01-02",
      "day_of_week": 5,
      "status": "missed",
      "checkin_count": 0,
      "is_today": false,
      "is_rest_suggested": false
    },
    {
      "date": "2026-01-03",
      "day_of_week": 6,
      "status": "rest_suggested",
      "checkin_count": 0,
      "is_today": false,
      "is_rest_suggested": true
    },
    {
      "date": "2026-01-04",
      "day_of_week": 0,
      "status": "today",
      "checkin_count": 1,
      "is_today": true,
      "is_rest_suggested": false
    },
    {
      "date": "2026-01-05",
      "day_of_week": 1,
      "status": "tomorrow_suggested",
      "checkin_count": 0,
      "is_today": false,
      "is_rest_suggested": false,
      "suggested_tasks_preview": ["复习极限运算法则", "练习题第3章"]
    }
  ]
}

// status 枚举:
// "checked_in"         → 已打卡（赤陶柔背景）
// "missed"             → 未打卡（虚线边框）
// "rest_suggested"     → 休息日（灰色小点）
// "today"              → 今日（深色强调）
// "tomorrow_suggested" → 明日推荐（鼠尾草色）
```

**GET /calendar/today**
```json
{
  "date": "2026-01-04",
  "tasks": [
    { "id": 1, "name": "背单词30分钟", "subject": "英语", "task_type": "main", "suggested_duration": 30, "completed": false, "is_review": false },
    { "id": 2, "name": "做数学练习题", "subject": "数学", "task_type": "main", "suggested_duration": 45, "completed": true, "is_review": false }
  ],
  "checkin_count": 1,
  "total_tasks": 2
}
```

**GET /calendar/tomorrow**
```json
{
  "date": "2026-01-05",
  "recommended_tasks": [
    {
      "task_name": "复习极限运算法则",
      "subject": "数学",
      "difficulty": "high",
      "suggested_duration": 40,
      "reason": "基于遗忘曲线，该知识点需要第2次复习"
    }
  ],
  "rest_suggested": false,
  "rest_reason": ""
}
```

### 4.7 设置服务

| 接口 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 获取/更新提醒 | GET/PUT | /settings/reminder | 读取/更新提醒设置 |
| 导出PDF报告 | GET | /report/pdf | 生成并返回用户学习报告PDF |
| 获取小组信息 | GET | /groups/my | 获取当前用户小组信息 |
| 加入小组 | POST | /groups/join | 通过邀请码加入小组 |
| 管理小组 | PUT | /groups/{id} | 更新小组信息（仅创建者） |

#### 请求/响应示例

**PUT /settings/reminder**
```json
// Request
{
  "reminder_enabled": true,
  "reminder_time": "21:00:00",
  "task_expire_notify": true
}
```

**GET /groups/my**
```json
{
  "group": {
    "id": 1,
    "name": "考研学习小组",
    "member_count": 15,
    "completion_rate": 78.5
  },
  "my_rank_range": "top_20"
}
```

---

## 五、核心算法设计

### 5.1 规律性计算算法

**算法公式：**
```
规律性得分 = max(0, 100 - (标准差 / 平均打卡时间) × 100)
```
> 权重系数为 1.0（默认值），后续可根据实际数据分布调整。

**计算步骤：**
1. 获取用户最近 30 天所有打卡时间
2. 提取每次打卡的小时数（0-23，精确到分钟）
3. 计算所有打卡时间的平均值
4. 计算标准差（衡量时间波动程度）
5. 计算波动系数 = 标准差 / 平均值
6. 规律性得分 = clamp(100 - 波动系数 × 100, 0, 100)

**参与条件：** 至少 7 次打卡记录（checkins >= 7），否则返回 "insufficient"

**排名区间划分：**
```
得分从高到低排序后按百分比划分：
  前 20%      → "top_20"    → "规律达人"
  20% - 60%   → "top_60"    → "习惯养成者"  
  60%+        → "bottom_40" → "继续加油"
```

### 5.2 遗忘曲线算法

**复习时间点：** 从原任务最后一次打卡完成日开始计算

| 复习轮次 | 间隔 | 标记 |
| --- | --- | --- |
| review_round=1 | 1天后 | 第1次复习 |
| review_round=2 | 2天后 | 第2次复习 |
| review_round=3 | 4天后 | 第3次复习 |
| review_round=4 | 7天后 | 第4次复习 |
| review_round=5 | 15天后 | 第5次复习（最终） |

**触发时机：** 用户完成打卡任务 → 后端异步创建 `is_review_task=true, parent_task_id=原任务ID` 的复习子任务

**知识掌握状态流转：**
```
新学 → 第1次复习完成 → 第2次复习完成 → ... → 第5次复习完成 → 已掌握
```

### 5.3 进度预估算法

**公式：**
```
剩余天数 = 剩余任务数 × 平均完成天数 / 学习效率系数

学习效率系数 = 实际完成天数 / 预估完成天数 × 0.8 + 连续打卡系数 × 0.2
连续打卡系数 = min(当前连续天数 / 7, 1.0)
```

### 5.4 连续打卡天数计算

```
按天分组用户的 checkin 记录（去重日期）→ 从今天倒推连续天数：
  - 昨天有打卡 → streak += 1，继续往前推
  - 昨天无打卡但在休息建议日内 → 不中断，继续往前推
  - 昨天无打卡且非休息建议 → streak 断掉
```

---

## 六、安全设计

### 6.1 认证安全

| 措施 | 说明 |
| --- | --- |
| JWT认证 | 无状态认证，token有效期24小时；payload 含 `{ user_id, openid, role }` |
| 微信code2Session | 通过微信官方接口校验证code有效性 |
| 密码哈希 | 使用bcrypt进行密码哈希存储（邮箱登录场景） |
| 输入验证 | 所有输入进行格式验证和长度限制（前端+后端双重校验） |

### 6.2 权限模型

| 层级 | 判断方式 | 范围 |
| --- | --- | --- |
| **普通用户** | 默认 | 仅能操作自己的数据（tasks/checkins/stats 按 user_id 隔离） |
| **小组管理员** | `groups.creator_id == user.id` | 管理自己创建的小组（更新小组信息、后续可移除成员） |
| **系统管理员** | `users.role == 'admin'`（DB 手动设置） | 预留 `require_admin()` 中间件，后续开发 `/admin/*` 端点 |

> MVP 阶段所有用户 role 均为 `'user'`，管理员功能不在 MVP 范围内。`require_admin()` 中间件已预留但暂不挂载到任何路由。

### 6.3 数据安全

| 措施 | 说明 |
| --- | --- |
| 数据加密 | 敏感数据传输使用HTTPS |
| 权限控制 | 所有接口基于JWT user_id校验资源归属 |
| 输入过滤 | SQLAlchemy ORM参数化查询，防SQL注入 |
| XSS防护 | 用户输入在渲染前转义处理 |
| API密钥管理 | DeepSeek API Key仅存储在服务端环境变量，前端不可见 |

### 6.4 限流设计

| 接口 | 限流规则 |
| --- | --- |
| /ai/* | 每个用户每日10次 |
| /checkins/ | 同一task_id每分钟最多3次（防抖） |

### 6.5 客户端鉴权与 Token 管理

**JWT token 过期处理流程：**

```
前端 API 拦截器检测到 401 响应
    ↓
清除本地过期 token
    ↓
调用 wx.login() 获取新 code
    ↓
POST /auth/wechat-login { code }（静默重授权，无需用户手动操作）
    ↓
后端返回新 JWT token
    ↓
前端更新本地 token → 重放原始请求
    ↓
用户无感知恢复操作（不丢失当前页面上下文）
```

> 微信测试号 code 有效期为 5 分钟，需在获取后立即使用。
> 正式号上线时可引入 refresh_token 机制（当前测试号阶段 JWT 24h 已满足开发调试）。

### 6.6 边界条件与错误处理

#### 打卡幂等性

```
POST /checkins/ 后端逻辑：
1. 检查 (user_id, task_id, checkin_date) 唯一约束
2. 同一用户同一任务同一天已有记录 → 200 + 返回已有记录（幂等），而非 409 报错
3. 同一分钟同一 task_id 超过 3 次 → 429（前端防抖 + 后端限流双重保障）
```

> checkins 表增加复合唯一索引：`UNIQUE(user_id, task_id, DATE(checkin_time))`

#### AI 计划日期校验

```
POST /ai/generate-plan 返回后：
1. 后端对每个 scheduled_date 做范围校验：
   - scheduled_date 须在 [今天, 今天+365天] 区间内
   - 超出范围的子任务过滤并记录日志
   - 若全部子任务均被过滤 → 返回 422 + "AI 无法生成有效的日期计划，请调整输入"
2. 前端渲染前二次校验：非法日期的任务打标记 + 提示用户手动调整日期
```

#### AI API 调用的容错与重试

```
POST /ai/generate-plan 调用 DeepSeek API：
1. Prompt 约束：强调"只返回合法 JSON，不含 markdown 代码块"
2. JSON 解析失败 → 重试（最多 3 次）：
   - 第 1 次失败：调整 prompt 强调格式
   - 第 2 次失败：降级 temperature（降低随机性）
   - 第 3 次失败：返回 500 + { "detail": "AI 规划暂时不可用，请稍后重试或使用自定义计划" }
3. 网络超时：DeepSeek 调用超时 30s
```

---

## 七、环境配置

### 7.1 前端配置

`src/config.ts`：
```typescript
export const config = {
  dev: {
    apiBaseUrl: 'http://localhost:8000',
    debug: true,
  },
  staging: {
    apiBaseUrl: 'https://staging-api.example.com',
    debug: true,
  },
  prod: {
    apiBaseUrl: 'https://api.example.com',
    debug: false,
  },
};
```

### 7.2 后端环境变量

| 变量名 | 说明 | 示例 |
| --- | --- | --- |
| DATABASE_URL | 数据库连接地址 | `sqlite:///./learning_tracker.db` |
| JWT_SECRET_KEY | JWT签名密钥 | `your-secret-key-change-in-production` |
| JWT_ALGORITHM | JWT算法 | `HS256` |
| JWT_EXPIRE_MINUTES | JWT过期时间 | `1440` (24小时) |
| WECHAT_APPID | 微信小程序AppID | `wx1234567890abcdef` |
| WECHAT_APPSECRET | 微信小程序AppSecret | 仅后端使用 |
| DEEPSEEK_API_KEY | DeepSeek API Key | `sk-xxx` |
| DEEPSEEK_API_BASE | DeepSeek API地址 | `https://api.deepseek.com/v1` |

---

## 八、迁移清单：测试号 → 正式号

| 步骤 | 操作 | 涉及文件 |
| --- | --- | --- |
| 1 | 更换 AppID | `project.config.json` |
| 2 | 配置服务器域名白名单（request + uploadFile 合法域名） | 微信管理后台 |
| 3 | 更新前端 API BaseURL | `src/config.ts` |
| 4 | 更新后端 `WECHAT_APPID` / `WECHAT_APPSECRET` 环境变量 | `.env.prod` |
| 5 | 部署后端到生产服务器（HTTPS） | — |
| 6 | 启用模板消息（`wx.requestSubscribeMessage`），替换测试号的本地弹窗 | 前端提醒模块 |
| 7 | 提交微信审核 → 发布 | 微信开发者工具 |

---

## 九、待确认事项

| 序号 | 问题 | 状态 | 确认结果 |
| --- | --- | --- | --- |
| 1 | AI复习任务的插入是否需要用户手动确认？ | ✅ 已确认 | 用户收到通知后手动确认 |
| 2 | 补打卡时间限制？ | ✅ 已确认 | 最近7天 |
| 3 | 是否需要支持微信登录？ | ✅ 已确认 | 是，主鉴权方式为 `wx.login()` + openid |
| 4 | PDF导出功能是否需要实现？ | ✅ 已确认 | 是 |
| 5 | 是否需要支持小组/班级功能？ | ✅ 已确认 | 是（基础版） |
| 6 | AI模型选用？ | ✅ 已确认 | DeepSeek |
| 7 | 排行榜维度支持？ | ✅ 已确认 | 小组 / 全局 |
| 8 | 打卡提醒方式？ | ✅ 已确认 | 测试号用本地弹窗，正式号用模板消息 |
| 9 | AI生成任务是否需要用户二次编辑？ | ✅ 已确认 | 需要，支持内联编辑后确认创建 |
| 10 | 语音输入方案？ | ✅ 已确认 | 微信原生录音 + 后端语音识别 |
| 11 | 每日多次打卡？ | ✅ 已确认 | 支持 |
| 12 | 支持设置时间范围？ | ✅ 已确认 | 支持（start_date / end_date） |
