"""
任务管理路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Task
from schemas import (
    TaskCreate, TaskBatchCreate, TaskUpdate,
    TaskOut, TaskBatchOut,
)
from auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.post("/", response_model=TaskOut)
async def create_task(
    req: TaskCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建单个打卡任务"""
    task = Task(
        user_id=user.id,
        name=req.name,
        description=req.description or "",
        subject=req.subject or "",
        suggested_duration=req.suggested_duration or 25,
        task_type=req.task_type or "main",
        repeat_days=req.repeat_days if req.repeat_days is not None else 127,
        difficulty=req.difficulty or "medium",
        start_date=req.start_date,
        end_date=req.end_date,
        status="active",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.post("/batch", response_model=TaskBatchOut)
async def batch_create_tasks(
    req: TaskBatchCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量创建任务（AI 规划页确认后调用）"""
    created_tasks = []
    for task_data in req.tasks:
        task = Task(
            user_id=user.id,
            name=task_data.name,
            description=task_data.description or "",
            subject=task_data.subject or "",
            suggested_duration=task_data.suggested_duration or 25,
            task_type=task_data.task_type or "main",
            repeat_days=task_data.repeat_days if task_data.repeat_days is not None else 127,
            difficulty=task_data.difficulty or "medium",
            start_date=task_data.start_date,
            end_date=task_data.end_date,
            status="active",
        )
        db.add(task)
        created_tasks.append(task)

    db.commit()
    for t in created_tasks:
        db.refresh(t)

    return TaskBatchOut(
        created_count=len(created_tasks),
        tasks=[TaskOut.model_validate(t) for t in created_tasks],
    )


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    status: str = Query(None, description="按状态筛选 active/completed/expired/deleted"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户任务列表"""
    query = db.query(Task).filter(Task.user_id == user.id)
    if status:
        query = query.filter(Task.status == status)
    else:
        # 默认不返回已删除的
        query = query.filter(Task.status != "deleted")

    # 按创建时间倒序
    query = query.order_by(Task.created_at.desc())
    tasks = query.all()
    return [TaskOut.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取任务详情"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskOut.model_validate(task)


@router.put("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int,
    req: TaskUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新任务"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """软删除任务（status='deleted'），保留历史打卡记录"""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status == "deleted":
        raise HTTPException(status_code=400, detail="任务已被删除")

    task.status = "deleted"
    task.updated_at = datetime.utcnow()
    db.commit()

    return {"message": "任务已删除"}
