"""Check-in routes."""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Checkin, Task, User
from schemas import CheckinBackfill, CheckinCreate, CheckinOut, CheckinUpdate

router = APIRouter(prefix="/checkins", tags=["打卡记录"])


def parse_date_param(value: Optional[str], name: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{name} 格式错误，应为 YYYY-MM-DD")


def get_existing_checkin(db: Session, user_id: int, task_id: int, checkin_date: date) -> Optional[Checkin]:
    return (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user_id,
            Checkin.task_id == task_id,
            Checkin.checkin_date == checkin_date,
        )
        .first()
    )


def create_checkin_record(
    db: Session,
    user: User,
    task: Task,
    checkin_time: datetime,
    checkin_date: date | None = None,
) -> Checkin:
    task_date = checkin_date or checkin_time.date()
    existing = get_existing_checkin(db, user.id, task.id, task_date)
    if existing:
        return existing

    checkin = Checkin(
        user_id=user.id,
        task_id=task.id,
        subject=task.subject or "",
        checkin_date=task_date,
        checkin_time=checkin_time,
        is_review=False,
        review_round=0,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.post("/", response_model=CheckinOut)
async def create_checkin(
    req: CheckinCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create one check-in for a task instance."""
    task = db.query(Task).filter(Task.id == req.task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status in ("deleted", "expired"):
        raise HTTPException(status_code=400, detail="任务不可打卡")

    checkin = create_checkin_record(
        db,
        user,
        task,
        req.checkin_time or datetime.utcnow(),
        checkin_date=task.start_date,
    )
    return CheckinOut.model_validate(checkin)


@router.post("/backfill", response_model=CheckinOut)
async def backfill_checkin(
    req: CheckinBackfill,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Backfill one check-in within the latest 7 days."""
    today = date.today()
    min_date = today - timedelta(days=7)
    if req.checkin_date < min_date:
        raise HTTPException(status_code=400, detail="补打卡不可超过7天")
    if req.checkin_date > today:
        raise HTTPException(status_code=400, detail="不可补未来的打卡")

    task = db.query(Task).filter(Task.id == req.task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    checkin_time = datetime.combine(req.checkin_date, datetime.min.time().replace(hour=12))
    checkin = create_checkin_record(db, user, task, checkin_time, checkin_date=req.checkin_date)
    return CheckinOut.model_validate(checkin)


@router.get("/", response_model=list[CheckinOut])
async def list_checkins(
    task_id: int = Query(None),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List check-ins."""
    start = parse_date_param(start_date, "start_date")
    end = parse_date_param(end_date, "end_date")

    query = db.query(Checkin).filter(Checkin.user_id == user.id)
    if task_id:
        query = query.filter(Checkin.task_id == task_id)
    if start:
        query = query.filter(Checkin.checkin_date >= start)
    if end:
        query = query.filter(Checkin.checkin_date <= end)

    checkins = (
        query
        .order_by(Checkin.checkin_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [CheckinOut.model_validate(checkin) for checkin in checkins]


@router.get("/{checkin_id}", response_model=CheckinOut)
async def get_checkin(
    checkin_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get one check-in."""
    checkin = (
        db.query(Checkin)
        .filter(Checkin.id == checkin_id, Checkin.user_id == user.id)
        .first()
    )
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")
    return CheckinOut.model_validate(checkin)


@router.put("/{checkin_id}", response_model=CheckinOut)
async def update_checkin(
    checkin_id: int,
    req: CheckinUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one check-in."""
    checkin = (
        db.query(Checkin)
        .filter(Checkin.id == checkin_id, Checkin.user_id == user.id)
        .first()
    )
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")

    update_data = req.model_dump(exclude_unset=True)
    if "checkin_time" in update_data and update_data["checkin_time"] is not None:
        checkin.checkin_time = update_data["checkin_time"]
        checkin.checkin_date = update_data["checkin_time"].date()
    if "subject" in update_data and update_data["subject"] is not None:
        checkin.subject = update_data["subject"]

    db.commit()
    db.refresh(checkin)
    return CheckinOut.model_validate(checkin)


@router.delete("/{checkin_id}")
async def delete_checkin(
    checkin_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one check-in."""
    checkin = (
        db.query(Checkin)
        .filter(Checkin.id == checkin_id, Checkin.user_id == user.id)
        .first()
    )
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")

    db.delete(checkin)
    db.commit()
    return {"message": "打卡记录已删除"}
