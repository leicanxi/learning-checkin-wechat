# Flat Task Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the MVP runtime model so every task is a flat daily task instance exposed through canonical `name`, `task_date`, `completed`, and `checkin_id` fields.

**Architecture:** Keep the existing `tasks` table and router structure, but expose canonical fields through schemas and API responses. Treat old fields as compatibility storage during migration: `start_date` backs `task_date`, while `repeat_days`, `end_date`, review fields, and `Task.status=completed` stop driving runtime behavior. Frontend pages consume canonical task responses instead of recomputing task/check-in state.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, SQLite, WeChat Mini Program JavaScript.

---

## File Map

- Modify `backend/models.py`: add canonical storage columns where missing (`knowledge_tags`, `source`, `checkin_date`) while retaining legacy fields.
- Modify `backend/schemas.py`: add canonical task create/update/output schemas and AI task shape.
- Modify `backend/routers/tasks_router.py`: accept `task_date`, return `completed/checkin_id`, support date/range filtering, keep old clients compatible.
- Modify `backend/routers/checkins_router.py`: create check-ins by `task_id`, set `checkin_date`, enforce one check-in per task/date, stop mutating task status.
- Modify `backend/routers/calendar_router.py`: derive month/today/tomorrow from task instances and check-ins.
- Modify `backend/routers/stats_router.py`: compute completion rate from task instances.
- Modify `backend/routers/ai_router.py`: convert provider fields to canonical task fields in frontend response.
- Modify `miniapp/pages/home/home.js`: use `GET /tasks?date=today`, `completed`, and `checkin_id`.
- Modify `miniapp/pages/planner/planner.js`: store/send `name` and `task_date` instead of `task_name` and `scheduled_date`.
- Modify `miniapp/pages/calendar/calendar.js`: consume simplified month statuses.

## Task 1: Backend Schema Contract

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add compatibility columns**

Add `knowledge_tags`, `source`, and `checkin_date` columns. Keep legacy columns for migration.

```python
knowledge_tags = Column(Text, nullable=True)
source = Column(String(20), default="manual")
checkin_date = Column(Date, nullable=True)
```

- [ ] **Step 2: Add canonical Pydantic fields**

Expose `task_date`, `knowledge_tags`, `source`, `completed`, and `checkin_id` in task schemas. Keep accepting legacy `start_date` only as a fallback during migration.

- [ ] **Step 3: Run import check**

Run: `python -m py_compile backend/models.py backend/schemas.py`

Expected: exits 0.

## Task 2: Task Router Canonical Runtime

**Files:**
- Modify: `backend/routers/tasks_router.py`

- [ ] **Step 1: Add response builder**

Create a helper that maps model rows to canonical response fields and joins same-day check-ins.

```python
def build_task_out(task, checkin=None):
    return TaskOut(
        id=task.id,
        user_id=task.user_id,
        name=task.name,
        task_date=task.start_date,
        subject=task.subject or "",
        suggested_duration=task.suggested_duration or 25,
        difficulty=task.difficulty or "medium",
        knowledge_tags=parse_json_list(task.knowledge_tags),
        source=task.source or ("ai" if task.is_ai_generated else "manual"),
        status=task.status if task.status != "completed" else "active",
        completed=checkin is not None,
        checkin_id=checkin.id if checkin else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
```

- [ ] **Step 2: Update create and batch create**

Accept canonical `task_date`, write it into legacy `start_date`, set `end_date` equal to `task_date` for flat instances, set `source` and `is_ai_generated`.

- [ ] **Step 3: Update list filtering**

Support `date`, `start`, and `end` query params. If old `status=active` is passed, keep it working but normalize stored `completed` tasks as active for runtime.

- [ ] **Step 4: Run compile check**

Run: `python -m py_compile backend/routers/tasks_router.py`

Expected: exits 0.

## Task 3: Check-In Router Canonical Runtime

**Files:**
- Modify: `backend/routers/checkins_router.py`

- [ ] **Step 1: Use local check-in date**

Set `checkin_date = checkin_time.date()` for MVP and store it on the check-in record.

- [ ] **Step 2: Enforce one check-in per task/date**

Find existing check-ins by `user_id`, `task_id`, and `checkin_date` first. Fall back to timestamp day-range only for old rows where `checkin_date` is null.

- [ ] **Step 3: Stop mutating task status**

Remove the logic that sets `task.status = "completed"` after check-in.

- [ ] **Step 4: Run compile check**

Run: `python -m py_compile backend/routers/checkins_router.py`

Expected: exits 0.

## Task 4: Calendar and Stats Runtime

**Files:**
- Modify: `backend/routers/calendar_router.py`
- Modify: `backend/routers/stats_router.py`

- [ ] **Step 1: Calendar month statuses**

Use tasks where `start_date` is in month and `status != deleted`. For each date, derive:

```text
checked_in: has tasks and all have checkins
pending: has tasks, incomplete, today/future
missed: has tasks, incomplete, past
empty: no tasks
```

- [ ] **Step 2: Today tasks**

Return only tasks where `task_date == today`; include `completed` from check-ins.

- [ ] **Step 3: Stats completion rate**

Use `completed task count / scheduled active task count` for weekly and monthly rates.

- [ ] **Step 4: Run compile check**

Run: `python -m py_compile backend/routers/calendar_router.py backend/routers/stats_router.py`

Expected: exits 0.

## Task 5: AI and Planner Field Alignment

**Files:**
- Modify: `backend/schemas.py`
- Modify: `backend/routers/ai_router.py`
- Modify: `miniapp/pages/planner/planner.js`

- [ ] **Step 1: Canonical AI frontend response**

Return `tasks` with `name`, `task_date`, `subject`, `suggested_duration`, `difficulty`, `knowledge_tags`, and `source`.

- [ ] **Step 2: Planner internal field names**

Use `name` and `task_date` in `planItems`. Convert user custom entries to the same shape.

- [ ] **Step 3: Batch submit canonical payload**

Send `POST /tasks/batch` with canonical task objects.

## Task 6: Home and Calendar Frontend Consumers

**Files:**
- Modify: `miniapp/pages/home/home.js`
- Modify: `miniapp/pages/calendar/calendar.js`

- [ ] **Step 1: Home tasks**

Replace `/tasks?status=active` plus `/checkins` merge with `GET /tasks?date=today`. Use `completed` and `checkin_id`.

- [ ] **Step 2: Home check-in toggle**

If `completed`, delete `checkin_id`; otherwise post `{ task_id }`.

- [ ] **Step 3: Calendar status mapping**

Map `checked_in`, `pending`, `missed`, and `empty`. Keep visual classes stable for MVP.

## Task 7: Verification

**Files:**
- No source edits unless verification exposes a defect.

- [ ] **Step 1: Compile backend**

Run:

```powershell
python -m py_compile backend/models.py backend/schemas.py backend/routers/tasks_router.py backend/routers/checkins_router.py backend/routers/calendar_router.py backend/routers/stats_router.py backend/routers/ai_router.py
```

Expected: exits 0.

- [ ] **Step 2: Search forbidden new frontend/API names**

Run:

```powershell
Select-String -Path 'miniapp/pages/*/*.js','backend/schemas.py','backend/routers/*.py' -Pattern 'task_name|scheduled_date|done'
```

Expected: only legacy compatibility code or display fallbacks remain.

- [ ] **Step 3: Review git diff**

Run: `git diff --stat`

Expected: changes are limited to the files in this plan.

