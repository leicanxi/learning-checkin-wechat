"""Temporary local debug console for test task data."""
import json
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Checkin, Group, Task, User, UserGroup

router = APIRouter(prefix="/debug", tags=["临时调试后台"])


def parse_date(value: str, field_name: str = "date") -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field_name} must be YYYY-MM-DD")


def dump_tags(value: Any) -> str:
    if isinstance(value, str):
        tags = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        tags = [str(item).strip() for item in value if str(item).strip()]
    else:
        tags = []
    return json.dumps(tags, ensure_ascii=False)


def load_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except json.JSONDecodeError:
        pass
    return []


def checkin_for_task(db: Session, task: Task) -> Checkin | None:
    return (
        db.query(Checkin)
        .filter(
            Checkin.user_id == task.user_id,
            Checkin.task_id == task.id,
            Checkin.checkin_date == task.start_date,
        )
        .first()
    )


def serialize_task(db: Session, task: Task) -> dict[str, Any]:
    checkin = checkin_for_task(db, task)
    return {
        "id": task.id,
        "user_id": task.user_id,
        "name": task.name,
        "description": task.description or "",
        "subject": task.subject or "",
        "suggested_duration": task.suggested_duration or 25,
        "difficulty": task.difficulty or "medium",
        "task_date": task.start_date.isoformat(),
        "status": task.status or "active",
        "source": task.source or ("ai" if task.is_ai_generated else "manual"),
        "knowledge_tags": load_tags(task.knowledge_tags),
        "completed": checkin is not None,
        "checkin_id": checkin.id if checkin else None,
    }


def set_task_completion(db: Session, task: Task, completed: bool) -> None:
    existing = checkin_for_task(db, task)
    if completed and not existing:
        checkin_time = datetime.combine(task.start_date, time(hour=12))
        db.add(Checkin(
            user_id=task.user_id,
            task_id=task.id,
            subject=task.subject or "",
            checkin_date=task.start_date,
            checkin_time=checkin_time,
            is_review=False,
            review_round=0,
        ))
    elif not completed and existing:
        db.delete(existing)


def make_debug_task(user_id: int, payload: dict[str, Any]) -> Task:
    task_date = parse_date(payload.get("task_date"), "task_date")
    source = payload.get("source") or "ai"
    return Task(
        user_id=user_id,
        name=(payload.get("name") or "测试任务").strip(),
        description=payload.get("description") or "",
        subject=payload.get("subject") or "",
        suggested_duration=int(payload.get("suggested_duration") or 25),
        task_type="main",
        repeat_days=0,
        difficulty=payload.get("difficulty") or "medium",
        start_date=task_date,
        end_date=task_date,
        status=payload.get("status") or "active",
        is_ai_generated=source == "ai",
        is_review_task=False,
        knowledge_tags=dump_tags(payload.get("knowledge_tags")),
        source=source,
    )


def serialize_group(db: Session, group: Group, selected_user_id: int | None = None) -> dict[str, Any]:
    member_count = (
        db.query(UserGroup)
        .filter(UserGroup.group_id == group.id)
        .count()
    )
    role = "none"
    if selected_user_id:
        membership = (
            db.query(UserGroup)
            .filter(UserGroup.group_id == group.id, UserGroup.user_id == selected_user_id)
            .first()
        )
        if membership:
          role = "owner" if group.creator_id == selected_user_id else "member"

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description or "",
        "invite_code": group.invite_code,
        "creator_id": group.creator_id,
        "member_count": member_count,
        "role_for_selected_user": role,
        "created_at": group.created_at.isoformat() if group.created_at else "",
    }


def get_user_group(db: Session, user_id: int) -> Group | None:
    membership = db.query(UserGroup).filter(UserGroup.user_id == user_id).first()
    if not membership:
        return None
    return db.query(Group).filter(Group.id == membership.group_id).first()


@router.get("/tasks", response_class=HTMLResponse)
async def debug_tasks_page():
    return HTMLResponse(DEBUG_TASKS_HTML)


@router.get("/api/users")
async def list_debug_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.desc()).limit(100).all()
    return [
        {
            "id": user.id,
            "nickname": user.nickname or "",
            "email": user.email or "",
            "openid": user.openid or "",
            "created_at": user.created_at.isoformat() if user.created_at else "",
        }
        for user in users
    ]


@router.post("/api/users")
async def create_debug_user(payload: dict[str, Any], db: Session = Depends(get_db)):
    nickname = (payload.get("nickname") or "Debug User").strip()
    stamp = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    user = User(
        nickname=nickname,
        email=f"debug-{stamp}@example.com",
        openid=f"debug-openid-{stamp}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "nickname": user.nickname, "email": user.email, "openid": user.openid}


@router.get("/api/users/{user_id}/group")
async def get_debug_user_group(user_id: int, db: Session = Depends(get_db)):
    group = get_user_group(db, user_id)
    if not group:
        return {"group": None, "members": []}
    members = debug_group_members(group.id, db)
    return {"group": serialize_group(db, group, user_id), "members": members}


@router.get("/api/groups")
async def list_debug_groups(db: Session = Depends(get_db)):
    groups = db.query(Group).order_by(Group.created_at.desc()).limit(100).all()
    return [serialize_group(db, group) for group in groups]


@router.post("/api/groups")
async def create_debug_group(payload: dict[str, Any], db: Session = Depends(get_db)):
    import random
    import string

    user_id = int(payload.get("user_id") or 0)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    if get_user_group(db, user_id):
        raise HTTPException(status_code=400, detail="user already has a group")

    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    while db.query(Group).filter(Group.invite_code == invite_code).first():
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    group = Group(
        name=(payload.get("name") or "Debug Group").strip(),
        description=payload.get("description") or "",
        invite_code=invite_code,
        creator_id=user_id,
    )
    db.add(group)
    db.flush()
    db.add(UserGroup(user_id=user_id, group_id=group.id))
    db.commit()
    db.refresh(group)
    return serialize_group(db, group, user_id)


@router.post("/api/groups/join")
async def join_debug_group(payload: dict[str, Any], db: Session = Depends(get_db)):
    user_id = int(payload.get("user_id") or 0)
    invite_code = (payload.get("invite_code") or "").strip().upper()
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="user not found")
    if get_user_group(db, user_id):
        raise HTTPException(status_code=400, detail="user already has a group")
    group = db.query(Group).filter(Group.invite_code == invite_code).first()
    if not group:
        raise HTTPException(status_code=404, detail="invalid invite code")
    db.add(UserGroup(user_id=user_id, group_id=group.id))
    db.commit()
    return serialize_group(db, group, user_id)


@router.delete("/api/users/{user_id}/group")
async def leave_debug_group(user_id: int, db: Session = Depends(get_db)):
    membership = db.query(UserGroup).filter(UserGroup.user_id == user_id).first()
    if not membership:
        return {"ok": True, "message": "user has no group"}
    group = db.query(Group).filter(Group.id == membership.group_id).first()
    db.delete(membership)
    if group and group.creator_id == user_id:
        remaining = (
            db.query(UserGroup)
            .filter(UserGroup.group_id == group.id, UserGroup.user_id != user_id)
            .count()
        )
        if remaining == 0:
            db.delete(group)
    db.commit()
    return {"ok": True}


def debug_group_members(group_id: int, db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(UserGroup, User)
        .join(User, User.id == UserGroup.user_id)
        .filter(UserGroup.group_id == group_id)
        .order_by(UserGroup.joined_at.asc())
        .all()
    )
    group = db.query(Group).filter(Group.id == group_id).first()
    return [
        {
            "user_id": user.id,
            "nickname": user.nickname or "用户",
            "email": user.email or "",
            "openid": user.openid or "",
            "role": "owner" if group and group.creator_id == user.id else "member",
            "joined_at": membership.joined_at.isoformat() if membership.joined_at else "",
        }
        for membership, user in rows
    ]


@router.get("/api/groups/{group_id}/members")
async def list_debug_group_members(group_id: int, db: Session = Depends(get_db)):
    return debug_group_members(group_id, db)


@router.delete("/api/groups/{group_id}/members/{user_id}")
async def remove_debug_group_member(group_id: int, user_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="group not found")
    if group.creator_id == user_id:
        raise HTTPException(status_code=400, detail="cannot remove group owner")
    membership = (
        db.query(UserGroup)
        .filter(UserGroup.group_id == group_id, UserGroup.user_id == user_id)
        .first()
    )
    if membership:
        db.delete(membership)
        db.commit()
    return {"ok": True}


@router.get("/api/tasks")
async def list_debug_tasks(user_id: int, date_filter: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Task).filter(Task.user_id == user_id, Task.status != "deleted")
    if date_filter:
        query = query.filter(Task.start_date == parse_date(date_filter, "date_filter"))
    tasks = query.order_by(Task.start_date.asc(), Task.created_at.asc()).all()
    return [serialize_task(db, task) for task in tasks]


@router.post("/api/tasks")
async def create_debug_task(payload: dict[str, Any], db: Session = Depends(get_db)):
    user_id = int(payload.get("user_id") or 0)
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="user not found")
    task = make_debug_task(user_id, payload)
    db.add(task)
    db.flush()
    set_task_completion(db, task, bool(payload.get("completed")))
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


@router.put("/api/tasks/{task_id}")
async def update_debug_task(task_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    old_date = task.start_date
    if "name" in payload:
        task.name = (payload.get("name") or "测试任务").strip()
    if "description" in payload:
        task.description = payload.get("description") or ""
    if "subject" in payload:
        task.subject = payload.get("subject") or ""
    if "suggested_duration" in payload:
        task.suggested_duration = int(payload.get("suggested_duration") or 25)
    if "difficulty" in payload:
        task.difficulty = payload.get("difficulty") or "medium"
    if "task_date" in payload:
        task.start_date = parse_date(payload.get("task_date"), "task_date")
        task.end_date = task.start_date
    if "status" in payload:
        task.status = payload.get("status") or "active"
    if "source" in payload:
        task.source = payload.get("source") or "ai"
        task.is_ai_generated = task.source == "ai"
    if "knowledge_tags" in payload:
        task.knowledge_tags = dump_tags(payload.get("knowledge_tags"))

    if old_date != task.start_date:
        for checkin in db.query(Checkin).filter(Checkin.task_id == task.id).all():
            checkin.checkin_date = task.start_date
            checkin.checkin_time = datetime.combine(task.start_date, time(hour=12))

    if "completed" in payload:
        set_task_completion(db, task, bool(payload.get("completed")))

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return serialize_task(db, task)


@router.delete("/api/tasks/{task_id}")
async def delete_debug_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    db.query(Checkin).filter(Checkin.task_id == task.id).delete()
    task.status = "deleted"
    task.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/api/seed-week")
async def seed_debug_week(payload: dict[str, Any], db: Session = Depends(get_db)):
    user_id = int(payload.get("user_id") or 0)
    start = parse_date(payload.get("start_date") or date.today().isoformat(), "start_date")
    if not db.query(User).filter(User.id == user_id).first():
        raise HTTPException(status_code=404, detail="user not found")

    created = []
    for offset in range(7):
        task_date = start + timedelta(days=offset)
        task = Task(
            user_id=user_id,
            name=f"调试任务 {offset + 1}",
            description="debug seed",
            subject="测试",
            suggested_duration=20 + offset * 5,
            task_type="main",
            repeat_days=0,
            difficulty=["low", "medium", "high"][offset % 3],
            start_date=task_date,
            end_date=task_date,
            status="active",
            is_ai_generated=True,
            is_review_task=False,
            knowledge_tags=dump_tags(["debug", f"day-{offset + 1}"]),
            source="ai",
        )
        db.add(task)
        db.flush()
        if offset in (0, 2):
            set_task_completion(db, task, True)
        created.append(task)

    db.commit()
    return {"created_count": len(created), "tasks": [serialize_task(db, task) for task in created]}


@router.delete("/api/users/{user_id}/tasks")
async def clear_debug_user_tasks(user_id: int, db: Session = Depends(get_db)):
    task_ids = [row.id for row in db.query(Task.id).filter(Task.user_id == user_id).all()]
    if task_ids:
        db.query(Checkin).filter(Checkin.task_id.in_(task_ids)).delete(synchronize_session=False)
        db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted_count": len(task_ids)}


DEBUG_TASKS_HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>临时任务调试后台</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; color: #222; }
    h1 { font-size: 22px; margin: 0 0 14px; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 10px 0; }
    input, select, button { height: 34px; padding: 0 8px; }
    button { cursor: pointer; }
    table { width: 100%; border-collapse: collapse; margin-top: 14px; }
    th, td { border: 1px solid #ddd; padding: 6px; font-size: 13px; vertical-align: middle; }
    th { background: #f6f6f6; text-align: left; }
    td input, td select { width: 100%; box-sizing: border-box; }
    .panel { border: 1px solid #ddd; padding: 12px; margin: 12px 0; }
    .muted { color: #777; font-size: 12px; }
    .ok { color: #0a7; }
    .bad { color: #b22; }
    .section-title { font-weight: 700; margin-bottom: 8px; }
    .group-box { background: #fafafa; border: 1px solid #e5e5e5; padding: 10px; margin-top: 8px; }
    .member-chip { display: inline-flex; gap: 6px; align-items: center; border: 1px solid #ddd; padding: 4px 6px; margin: 3px; font-size: 12px; }
  </style>
</head>
<body>
  <h1>临时任务调试后台</h1>
  <div class="muted">选择小程序当前登录的用户，再增删改任务。小程序日历刷新后会读取同一批数据。</div>

  <div class="panel">
    <div class="section-title">用户</div>
    <div class="row">
      <select id="userSelect" onchange="onUserChange()"></select>
      <button onclick="loadUsers()">刷新用户</button>
      <input id="newUserName" placeholder="新测试用户昵称" />
      <button onclick="createUser()">创建测试用户</button>
    </div>
    <div class="row">
      <input id="dateFilter" type="date" />
      <button onclick="shiftDate(-1)">前一天</button>
      <button onclick="setToday()">今天</button>
      <button onclick="shiftDate(1)">后一天</button>
      <button onclick="loadTasks()">加载当天任务</button>
      <button onclick="seedWeek()">生成未来 7 天</button>
      <button onclick="clearTasks()">清空该用户任务</button>
    </div>
  </div>

  <div class="panel">
    <div class="section-title">小组调试</div>
    <div id="groupStatus" class="group-box muted">未加载</div>
    <div class="row">
      <input id="newGroupName" placeholder="新小组名称" value="Debug 小组" />
      <button onclick="createGroup()">用当前用户创建小组</button>
      <input id="joinInviteCode" placeholder="邀请码" />
      <button onclick="joinGroup()">当前用户加入</button>
      <button onclick="leaveGroup()">当前用户退出小组</button>
    </div>
    <div id="groupMembers"></div>
  </div>

  <div class="panel">
    <div class="section-title">任务调试</div>
    <div class="row">
      <input id="taskName" placeholder="任务名" value="背单词" />
      <input id="taskSubject" placeholder="科目" value="英语" />
      <input id="taskDuration" type="number" value="25" style="width:80px" />
      <select id="taskDifficulty">
        <option value="low">low</option>
        <option value="medium" selected>medium</option>
        <option value="high">high</option>
      </select>
      <input id="taskTags" placeholder="标签，逗号分隔" value="debug" />
      <label><input id="taskCompleted" type="checkbox" /> 已完成</label>
      <button onclick="createTask()">新增当天任务</button>
    </div>
  </div>

  <div id="message" class="muted"></div>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>日期</th><th>名称</th><th>科目</th><th>分钟</th><th>难度</th><th>标签</th><th>完成</th><th>操作</th>
      </tr>
    </thead>
    <tbody id="taskRows"></tbody>
  </table>

  <script>
    const $ = id => document.getElementById(id)
    const api = (path, options = {}) => fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options
    }).then(async r => {
      const data = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(data.detail || r.statusText)
      return data
    })

    function todayString() {
      const d = new Date()
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    }

    function selectedUserId() {
      return Number($('userSelect').value)
    }

    function show(text, good = true) {
      $('message').className = good ? 'ok' : 'bad'
      $('message').textContent = text
    }

    async function loadUsers() {
      const users = await api('/debug/api/users')
      $('userSelect').innerHTML = users.map(u => {
        const label = `#${u.id} ${u.nickname || '(no nickname)'} ${u.email || u.openid || ''}`
        return `<option value="${u.id}">${label}</option>`
      }).join('')
      if (users.length) onUserChange()
    }

    function onUserChange() {
      loadTasks()
      loadUserGroup()
    }

    async function createUser() {
      await api('/debug/api/users', {
        method: 'POST',
        body: JSON.stringify({ nickname: $('newUserName').value || 'Debug User' })
      })
      await loadUsers()
      show('已创建测试用户')
    }

    async function loadUserGroup() {
      if (!selectedUserId()) return
      const res = await api(`/debug/api/users/${selectedUserId()}/group`)
      const group = res.group
      if (!group) {
        $('groupStatus').className = 'group-box muted'
        $('groupStatus').innerHTML = '当前用户未加入小组'
        $('groupMembers').innerHTML = ''
        return
      }
      $('groupStatus').className = 'group-box'
      $('groupStatus').innerHTML = `
        <div><b>#${group.id} ${escapeHtml(group.name)}</b></div>
        <div>角色：${group.role_for_selected_user === 'owner' ? '组长' : '成员'} · 成员 ${group.member_count} 人 · 邀请码 <b>${group.invite_code}</b></div>
      `
      $('joinInviteCode').value = group.invite_code
      renderGroupMembers(group.id, res.members || [])
    }

    function renderGroupMembers(groupId, members) {
      $('groupMembers').innerHTML = members.map(m => `
        <span class="member-chip">
          #${m.user_id} ${escapeHtml(m.nickname)} ${m.role === 'owner' ? '组长' : '成员'}
          ${m.role === 'owner' ? '' : `<button onclick="removeGroupMember(${groupId}, ${m.user_id})">移除</button>`}
        </span>
      `).join('')
    }

    async function createGroup() {
      await api('/debug/api/groups', {
        method: 'POST',
        body: JSON.stringify({ user_id: selectedUserId(), name: $('newGroupName').value || 'Debug 小组' })
      })
      await loadUserGroup()
      show('已创建小组')
    }

    async function joinGroup() {
      await api('/debug/api/groups/join', {
        method: 'POST',
        body: JSON.stringify({ user_id: selectedUserId(), invite_code: $('joinInviteCode').value })
      })
      await loadUserGroup()
      show('已加入小组')
    }

    async function leaveGroup() {
      await api(`/debug/api/users/${selectedUserId()}/group`, { method: 'DELETE' })
      await loadUserGroup()
      show('当前用户已退出小组')
    }

    async function removeGroupMember(groupId, userId) {
      await api(`/debug/api/groups/${groupId}/members/${userId}`, { method: 'DELETE' })
      await loadUserGroup()
      show('已移除小组成员')
    }

    async function loadTasks() {
      if (!selectedUserId()) return
      const date = $('dateFilter').value
      const rows = await api(`/debug/api/tasks?user_id=${selectedUserId()}&date_filter=${date}`)
      $('taskRows').innerHTML = rows.map(rowHtml).join('')
      show(`已加载 ${rows.length} 条任务`)
    }

    function rowHtml(t) {
      return `<tr data-id="${t.id}">
        <td>${t.id}</td>
        <td><input class="date" type="date" value="${t.task_date}"></td>
        <td><input class="name" value="${escapeHtml(t.name)}"></td>
        <td><input class="subject" value="${escapeHtml(t.subject)}"></td>
        <td><input class="duration" type="number" value="${t.suggested_duration}"></td>
        <td><select class="difficulty">
          ${['low', 'medium', 'high'].map(d => `<option value="${d}" ${t.difficulty === d ? 'selected' : ''}>${d}</option>`).join('')}
        </select></td>
        <td><input class="tags" value="${escapeHtml((t.knowledge_tags || []).join(','))}"></td>
        <td><input class="completed" type="checkbox" ${t.completed ? 'checked' : ''}></td>
        <td>
          <button onclick="saveTask(${t.id})">保存</button>
          <button onclick="deleteTask(${t.id})">删除</button>
        </td>
      </tr>`
    }

    function escapeHtml(value) {
      return String(value || '').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]))
    }

    function readRow(id) {
      const tr = document.querySelector(`tr[data-id="${id}"]`)
      return {
        task_date: tr.querySelector('.date').value,
        name: tr.querySelector('.name').value,
        subject: tr.querySelector('.subject').value,
        suggested_duration: Number(tr.querySelector('.duration').value || 25),
        difficulty: tr.querySelector('.difficulty').value,
        knowledge_tags: tr.querySelector('.tags').value,
        completed: tr.querySelector('.completed').checked,
        source: 'ai'
      }
    }

    async function createTask() {
      await api('/debug/api/tasks', {
        method: 'POST',
        body: JSON.stringify({
          user_id: selectedUserId(),
          task_date: $('dateFilter').value,
          name: $('taskName').value,
          subject: $('taskSubject').value,
          suggested_duration: Number($('taskDuration').value || 25),
          difficulty: $('taskDifficulty').value,
          knowledge_tags: $('taskTags').value,
          completed: $('taskCompleted').checked,
          source: 'ai'
        })
      })
      await loadTasks()
      show('已新增任务')
    }

    async function saveTask(id) {
      await api(`/debug/api/tasks/${id}`, { method: 'PUT', body: JSON.stringify(readRow(id)) })
      await loadTasks()
      show('已保存任务')
    }

    async function deleteTask(id) {
      await api(`/debug/api/tasks/${id}`, { method: 'DELETE' })
      await loadTasks()
      show('已删除任务')
    }

    async function seedWeek() {
      await api('/debug/api/seed-week', {
        method: 'POST',
        body: JSON.stringify({ user_id: selectedUserId(), start_date: $('dateFilter').value })
      })
      await loadTasks()
      show('已生成未来 7 天测试任务')
    }

    async function clearTasks() {
      if (!confirm('确认清空该用户所有任务和打卡？')) return
      const res = await api(`/debug/api/users/${selectedUserId()}/tasks`, { method: 'DELETE' })
      await loadTasks()
      show(`已清空 ${res.deleted_count} 条任务`)
    }

    function setToday() {
      $('dateFilter').value = todayString()
      loadTasks()
    }

    function shiftDate(delta) {
      const d = new Date($('dateFilter').value || todayString())
      d.setDate(d.getDate() + delta)
      $('dateFilter').value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      loadTasks()
    }

    $('dateFilter').value = todayString()
    loadUsers().catch(err => show(err.message, false))
  </script>
</body>
</html>
"""
