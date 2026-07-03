"""
打卡记录路由
"""
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Task, Checkin
from schemas import CheckinCreate, CheckinBackfill, CheckinUpdate, CheckinOut
from auth import get_current_user

router = APIRouter(prefix="/checkins", tags=["打卡记录"])


@router.post("/", response_model=CheckinOut)
async def create_checkin(
    req: CheckinCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """完成打卡"""
    # 校验任务存在且属于当前用户
    task = db.query(Task).filter(Task.id == req.task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ("active", "completed"):
        raise HTTPException(status_code=400, detail="任务不可打卡（已过期或已删除）")

    checkin_time = req.checkin_time or datetime.utcnow()

    # 幂等性：同一用户同一任务同一天已有记录 → 返回已有记录
    checkin_date_start = checkin_time.replace(hour=0, minute=0, second=0, microsecond=0)
    checkin_date_end = checkin_date_start + timedelta(days=1)
    existing = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user.id,
            Checkin.task_id == req.task_id,
            Checkin.checkin_time >= checkin_date_start,
            Checkin.checkin_time < checkin_date_end,
        )
        .first()
    )
    if existing:
        return CheckinOut.model_validate(existing)

    checkin = Checkin(
        user_id=user.id,
        task_id=req.task_id,
        subject=task.subject or "",
        checkin_time=checkin_time,
        is_review=req.is_review or False,
        review_round=0,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    # 标记任务完成状态
    if task.task_type != "review":
        all_today_checkins = (
            db.query(Checkin)
            .filter(
                Checkin.task_id == task.id,
                Checkin.checkin_time >= checkin_date_start,
                Checkin.checkin_time < checkin_date_end,
            )
            .count()
        )
        if all_today_checkins >= 1 and task.status == "active":
            task.status = "completed"
            task.updated_at = datetime.utcnow()
            db.commit()

    return CheckinOut.model_validate(checkin)


@router.post("/backfill", response_model=CheckinOut)
async def backfill_checkin(
    req: CheckinBackfill,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    补打卡最近 7 天
    """
    # 校验日期范围
    today = date.today()
    min_date = today - timedelta(days=7)
    if req.checkin_date < min_date:
        raise HTTPException(status_code=400, detail="补打卡不可超过7天")
    if req.checkin_date > today:
        raise HTTPException(status_code=400, detail="不可补未来的打卡")

    # 校验任务
    task = db.query(Task).filter(Task.id == req.task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 补打卡时间设为当天 12:00:00
    checkin_time = datetime.combine(req.checkin_date, datetime.min.time().replace(hour=12))

    # 幂等检查
    checkin_date_start = checkin_time.replace(hour=0, minute=0, second=0, microsecond=0)
    checkin_date_end = checkin_date_start + timedelta(days=1)
    existing = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user.id,
            Checkin.task_id == req.task_id,
            Checkin.checkin_time >= checkin_date_start,
            Checkin.checkin_time < checkin_date_end,
        )
        .first()
    )
    if existing:
        return CheckinOut.model_validate(existing)

    checkin = Checkin(
        user_id=user.id,
        task_id=req.task_id,
        subject=task.subject or "",
        checkin_time=checkin_time,
        is_review=False,
        review_round=0,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
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
    """获取打卡记录列表"""
    query = db.query(Checkin).filter(Checkin.user_id == user.id)

    if task_id:
        query = query.filter(Checkin.task_id == task_id)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Checkin.checkin_time >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 格式错误，应为 YYYY-MM-DD")

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Checkin.checkin_time < end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 格式错误，应为 YYYY-MM-DD")

    checkins = (
        query
        .order_by(Checkin.checkin_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [CheckinOut.model_validate(c) for c in checkins]


@router.get("/{checkin_id}", response_model=CheckinOut)
async def get_checkin(
    checkin_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取打卡详情"""
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
    """更新打卡记录"""
    checkin = (
        db.query(Checkin)
        .filter(Checkin.id == checkin_id, Checkin.user_id == user.id)
        .first()
    )
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(checkin, key, value)

    db.commit()
    db.refresh(checkin)
    return CheckinOut.model_validate(checkin)


@router.delete("/{checkin_id}")
async def delete_checkin(
    checkin_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除打卡记录"""
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
