"""Task-instance management routes."""
import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Checkin, Task, User
from schemas import TaskBatchCreate, TaskBatchOut, TaskCreate, TaskOut, TaskUpdate
from auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["任务管理"])


def parse_date_param(value: Optional[str], name: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{name} 格式错误，应为 YYYY-MM-DD")


def parse_tags(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except json.JSONDecodeError:
        pass
    return []


def dump_tags(tags: Optional[list[str]]) -> str:
    return json.dumps(tags or [], ensure_ascii=False)


def runtime_status(task: Task) -> str:
    return "active" if task.status == "completed" else (task.status or "active")


def build_task_out(task: Task, checkin: Optional[Checkin] = None) -> TaskOut:
    return TaskOut(
        id=task.id,
        user_id=task.user_id,
        name=task.name,
        description=task.description or "",
        subject=task.subject or "",
        suggested_duration=task.suggested_duration or 25,
        difficulty=task.difficulty or "medium",
        task_date=task.start_date,
        knowledge_tags=parse_tags(task.knowledge_tags),
        source=task.source or ("ai" if task.is_ai_generated else "manual"),
        status=runtime_status(task),
        completed=checkin is not None,
        checkin_id=checkin.id if checkin else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def make_task(req: TaskCreate, user_id: int) -> Task:
    source = req.source or "manual"
    return Task(
        user_id=user_id,
        name=req.name,
        description=req.description or "",
        subject=req.subject or "",
        suggested_duration=req.suggested_duration or 25,
        task_type="main",
        repeat_days=0,
        difficulty=req.difficulty or "medium",
        start_date=req.task_date,
        end_date=req.task_date,
        status="active",
        is_ai_generated=source == "ai",
        is_review_task=False,
        knowledge_tags=dump_tags(req.knowledge_tags),
        source=source,
    )


def load_checkins_for_tasks(db: Session, user_id: int, tasks: list[Task]) -> dict[tuple[int, date], Checkin]:
    task_ids = [task.id for task in tasks]
    if not task_ids:
        return {}

    rows = (
        db.query(Checkin)
        .filter(Checkin.user_id == user_id, Checkin.task_id.in_(task_ids))
        .all()
    )
    return {
        (row.task_id, row.checkin_date or row.checkin_time.date()): row
        for row in rows
    }


@router.post("/", response_model=TaskOut)
async def create_task(
    req: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create one flat task instance."""
    task = make_task(req, user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return build_task_out(task)


@router.post("/batch", response_model=TaskBatchOut)
async def batch_create_tasks(
    req: TaskBatchCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create multiple flat task instances."""
    created_tasks = []
    for task_data in req.tasks:
        task = make_task(task_data, user.id)
        db.add(task)
        created_tasks.append(task)

    db.commit()
    for task in created_tasks:
        db.refresh(task)

    return TaskBatchOut(
        created_count=len(created_tasks),
        tasks=[build_task_out(task) for task in created_tasks],
    )


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    date_filter: Optional[str] = Query(None, alias="date", description="任务日期 YYYY-MM-DD"),
    start: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="active/expired/deleted"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List flat task instances with derived completion state."""
    target_date = parse_date_param(date_filter, "date")
    start_date = parse_date_param(start, "start")
    end_date = parse_date_param(end, "end")

    query = db.query(Task).filter(Task.user_id == user.id)
    if status:
        if status == "active":
            query = query.filter(Task.status.in_(["active", "completed"]))
        else:
            query = query.filter(Task.status == status)
    else:
        query = query.filter(Task.status != "deleted")

    if target_date:
        query = query.filter(Task.start_date == target_date)
    if start_date:
        query = query.filter(Task.start_date >= start_date)
    if end_date:
        query = query.filter(Task.start_date <= end_date)

    tasks = query.order_by(Task.start_date.asc(), Task.created_at.asc()).all()
    checkins = load_checkins_for_tasks(db, user.id, tasks)
    return [
        build_task_out(task, checkins.get((task.id, task.start_date)))
        for task in tasks
    ]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one task instance."""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    checkin = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user.id,
            Checkin.task_id == task.id,
            Checkin.checkin_date == task.start_date,
        )
        .first()
    )
    return build_task_out(task, checkin)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    req: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one task instance."""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = req.model_dump(exclude_unset=True)
    if "task_date" in update_data:
        task.start_date = update_data.pop("task_date")
        task.end_date = task.start_date
    if "knowledge_tags" in update_data:
        task.knowledge_tags = dump_tags(update_data.pop("knowledge_tags"))
    if "source" in update_data:
        task.source = update_data["source"]
        task.is_ai_generated = update_data["source"] == "ai"

    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return build_task_out(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete one task instance."""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "deleted":
        raise HTTPException(status_code=400, detail="任务已被删除")

    task.status = "deleted"
    task.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "任务已删除"}
