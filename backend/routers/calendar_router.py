"""Calendar routes based on flat task instances."""
import calendar
import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Checkin, Task, User
from schemas import (
    CalendarDate,
    CalendarMonthResponse,
    CalendarTodayResponse,
    CalendarTomorrowResponse,
    TodayTaskItem,
    TomorrowRecommendedTask,
)

router = APIRouter(prefix="/calendar", tags=["日历服务"])


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item) for item in value]
    except json.JSONDecodeError:
        pass
    return []


def task_checkin_map(db: Session, user_id: int, tasks: list[Task]) -> dict[tuple[int, date], Checkin]:
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


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        return start, date(year + 1, 1, 1)
    return start, date(year, month + 1, 1)


@router.get("/month", response_model=CalendarMonthResponse)
async def get_month_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return calendar data for one month."""
    month_start, month_end = month_bounds(year, month)
    today = date.today()

    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.status != "deleted",
            Task.start_date >= month_start,
            Task.start_date < month_end,
        )
        .order_by(Task.start_date.asc(), Task.created_at.asc())
        .all()
    )
    checkins = task_checkin_map(db, user.id, tasks)

    tasks_by_date: dict[date, list[Task]] = defaultdict(list)
    for task in tasks:
        tasks_by_date[task.start_date].append(task)

    dates = []
    days_in_month = calendar.monthrange(year, month)[1]
    completed_tasks = 0
    scheduled_tasks = len(tasks)

    for day in range(1, days_in_month + 1):
        d = date(year, month, day)
        day_tasks = tasks_by_date.get(d, [])
        day_completed = [
            task for task in day_tasks
            if checkins.get((task.id, d)) is not None
        ]
        completed_tasks += len(day_completed)

        if not day_tasks:
            status = "empty"
        elif len(day_completed) == len(day_tasks):
            status = "checked_in"
        elif d < today:
            status = "missed"
        else:
            status = "pending"

        dates.append(CalendarDate(
            date=d.isoformat(),
            day_of_week=d.weekday(),
            status=status,
            checkin_count=len(day_completed),
            is_today=d == today,
            is_rest_suggested=False,
            suggested_tasks_preview=[task.name for task in day_tasks],
        ))

    monthly_completion_rate = (
        round(completed_tasks / scheduled_tasks * 100, 1)
        if scheduled_tasks else 0.0
    )

    return CalendarMonthResponse(
        year=year,
        month=month,
        monthly_completion_rate=monthly_completion_rate,
        dates=dates,
    )


@router.get("/today", response_model=CalendarTodayResponse)
async def get_today_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return today's task instances."""
    today = date.today()
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.status != "deleted",
            Task.start_date == today,
        )
        .order_by(Task.created_at.asc())
        .all()
    )
    checkins = task_checkin_map(db, user.id, tasks)

    items = []
    for task in tasks:
        checkin = checkins.get((task.id, today))
        items.append(TodayTaskItem(
            id=task.id,
            name=task.name,
            task_date=task.start_date,
            subject=task.subject or "",
            suggested_duration=task.suggested_duration or 25,
            difficulty=task.difficulty or "medium",
            knowledge_tags=parse_tags(task.knowledge_tags),
            source=task.source or ("ai" if task.is_ai_generated else "manual"),
            completed=checkin is not None,
            checkin_id=checkin.id if checkin else None,
        ))

    return CalendarTodayResponse(
        date=today.isoformat(),
        tasks=items,
        checkin_count=sum(1 for item in items if item.completed),
        total_tasks=len(items),
    )


@router.get("/tomorrow", response_model=CalendarTomorrowResponse)
async def get_tomorrow_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return tomorrow's scheduled task instances."""
    tomorrow = date.today() + timedelta(days=1)
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.status != "deleted",
            Task.start_date == tomorrow,
        )
        .order_by(Task.created_at.asc())
        .limit(5)
        .all()
    )

    recommended_tasks = [
        TomorrowRecommendedTask(
            name=task.name,
            task_date=task.start_date,
            subject=task.subject or "",
            difficulty=task.difficulty or "medium",
            suggested_duration=task.suggested_duration or 25,
            reason="明日计划任务",
        )
        for task in tasks
    ]

    return CalendarTomorrowResponse(
        date=tomorrow.isoformat(),
        recommended_tasks=recommended_tasks,
        rest_suggested=False,
        rest_reason="",
    )
