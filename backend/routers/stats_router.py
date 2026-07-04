"""Statistics routes based on flat task instances."""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Checkin, Task, User
from schemas import CheckinTrend, StatsResponse, SubjectDistribution

router = APIRouter(prefix="/stats", tags=["统计服务"])


def calculate_streak(user_id: int, db: Session) -> tuple[int, int]:
    rows = (
        db.query(Checkin.checkin_date)
        .filter(Checkin.user_id == user_id)
        .group_by(Checkin.checkin_date)
        .order_by(Checkin.checkin_date.desc())
        .all()
    )
    dates = sorted({row.checkin_date for row in rows if row.checkin_date})
    if not dates:
        return 0, 0

    today = date.today()
    current = 0
    cursor = today
    date_set = set(dates)
    while cursor in date_set:
        current += 1
        cursor -= timedelta(days=1)

    longest = 1
    running = 1
    for idx in range(1, len(dates)):
        if (dates[idx] - dates[idx - 1]).days == 1:
            running += 1
        else:
            longest = max(longest, running)
            running = 1
    longest = max(longest, running)
    return current, longest


def calculate_completion_rate(user_id: int, days: int, db: Session) -> float:
    today = date.today()
    start = today - timedelta(days=days - 1)

    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status != "deleted",
            Task.start_date >= start,
            Task.start_date <= today,
        )
        .all()
    )
    if not tasks:
        return 0.0

    task_ids = [task.id for task in tasks]
    checkins = (
        db.query(Checkin.task_id, Checkin.checkin_date)
        .filter(
            Checkin.user_id == user_id,
            Checkin.task_id.in_(task_ids),
        )
        .all()
    )
    completed_keys = {(row.task_id, row.checkin_date) for row in checkins}
    completed = sum(1 for task in tasks if (task.id, task.start_date) in completed_keys)
    return round(completed / len(tasks) * 100, 1)


@router.get("/", response_model=StatsResponse)
async def get_stats(
    period: str = Query("week", pattern="^(week|month|year)$"),
    start: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return user statistics."""
    current_streak, longest_streak = calculate_streak(user.id, db)
    weekly_rate = calculate_completion_rate(user.id, 7, db)
    monthly_rate = calculate_completion_rate(user.id, 30, db)

    total_checkins = (
        db.query(func.count(Checkin.id))
        .filter(Checkin.user_id == user.id)
        .scalar()
    ) or 0

    subject_rows = (
        db.query(Checkin.subject, func.count(Checkin.id).label("cnt"))
        .filter(Checkin.user_id == user.id, Checkin.subject != "")
        .group_by(Checkin.subject)
        .order_by(func.count(Checkin.id).desc())
        .all()
    )
    subject_distribution = [
        SubjectDistribution(
            subject=row.subject,
            count=row.cnt,
            percentage=round(row.cnt / total_checkins * 100, 1) if total_checkins else 0.0,
        )
        for row in subject_rows
    ]

    days_lookup = {"week": 7, "month": 30, "year": 365}
    trend_days = days_lookup.get(period, 7)
    try:
        trend_start = datetime.strptime(start, "%Y-%m-%d").date() if start else date.today() - timedelta(days=trend_days - 1)
        trend_end = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end 格式错误，应为 YYYY-MM-DD")

    trend_rows = (
        db.query(Checkin.checkin_date, func.count(Checkin.id).label("cnt"))
        .filter(
            Checkin.user_id == user.id,
            Checkin.checkin_date >= trend_start,
            Checkin.checkin_date <= trend_end,
        )
        .group_by(Checkin.checkin_date)
        .order_by(Checkin.checkin_date)
        .all()
    )
    checkin_trend = [
        CheckinTrend(date=row.checkin_date.isoformat(), count=row.cnt)
        for row in trend_rows
        if row.checkin_date
    ]

    active_tasks = (
        db.query(func.count(Task.id))
        .filter(Task.user_id == user.id, Task.status != "deleted", Task.start_date >= date.today())
        .scalar()
    ) or 0

    return StatsResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        weekly_rate=weekly_rate,
        monthly_rate=monthly_rate,
        total_checkins=total_checkins,
        knowledge_progress={"learning": 40, "reviewing": 30, "mastered": 30},
        subject_distribution=subject_distribution,
        checkin_trend=checkin_trend,
        estimated_remaining_days=active_tasks,
    )
