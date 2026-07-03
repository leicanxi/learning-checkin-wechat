"""
日历服务路由
"""
import calendar
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Task, Checkin
from schemas import (
    CalendarMonthResponse, CalendarDate,
    CalendarTodayResponse, CalendarTomorrowResponse,
    TodayTaskItem, TomorrowRecommendedTask,
)
from auth import get_current_user

router = APIRouter(prefix="/calendar", tags=["日历服务"])


def get_day_status(
    d: date,
    checkin_dates: set,
    rest_suggested_dates: set,
    suggested_tasks_map: dict,
    user_id: int,
    db: Session,
) -> CalendarDate:
    """判断某天的状态"""
    date_str = d.isoformat()
    today = date.today()

    is_today = (d == today)
    is_tomorrow = (d == today + timedelta(days=1))
    is_rest = d in rest_suggested_dates
    is_checked = d in checkin_dates

    if is_today:
        status = "today"
    elif is_checked:
        status = "checked_in"
    elif is_rest:
        status = "rest_suggested"
    elif is_tomorrow and d in suggested_tasks_map:
        status = "tomorrow_suggested"
    else:
        status = "missed"

    # 当日打卡次数
    checkin_count = 1 if is_checked else 0

    preview = suggested_tasks_map.get(d, None)

    return CalendarDate(
        date=date_str,
        day_of_week=d.weekday(),
        status=status,
        checkin_count=checkin_count,
        is_today=is_today,
        is_rest_suggested=is_rest,
        suggested_tasks_preview=preview,
    )


@router.get("/month", response_model=CalendarMonthResponse)
async def get_month_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取日历月视图数据"""
    # 获取当月所有打卡日期
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    checkin_rows = (
        db.query(func.date(Checkin.checkin_time).label("d"))
        .filter(
            Checkin.user_id == user.id,
            Checkin.checkin_time >= month_start,
            Checkin.checkin_time < month_end,
        )
        .group_by(func.date(Checkin.checkin_time))
        .all()
    )
    checkin_dates = {datetime.strptime(r.d, "%Y-%m-%d").date() for r in checkin_rows}

    # 获取当前连续天数判断是否需要休息建议
    today = date.today()
    # 获取最近 7 天打卡天数
    seven_days_ago = today - timedelta(days=7)
    recent_checkins = (
        db.query(func.count(func.distinct(func.date(Checkin.checkin_time))))
        .filter(
            Checkin.user_id == user.id,
            Checkin.checkin_time >= seven_days_ago,
        )
        .scalar()
    ) or 0

    # 连续打卡 >= 7 天的休息建议（当月内未来日期）
    rest_suggested_dates = set()
    if recent_checkins >= 7:
        for d_offset in range(1, 32):
            future_date = today + timedelta(days=d_offset)
            if future_date >= month_start and future_date < month_end:
                rest_suggested_dates.add(future_date)

    # 获取未来日期建议的任务
    suggested_tasks_map = {}
    future_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.status == "active",
            Task.start_date >= today,
            Task.start_date < month_end,
        )
        .all()
    )
    for t in future_tasks:
        if t.start_date not in suggested_tasks_map:
            suggested_tasks_map[t.start_date] = []
        suggested_tasks_map[t.start_date].append(t.name)

    # 构建日期列表
    dates = []
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        for day in week:
            if day == 0:
                dates.append(CalendarDate(
                    date=f"{year}-{month:02d}-01",
                    day_of_week=0,
                    status="missed",
                    checkin_count=0,
                    is_today=False,
                    is_rest_suggested=False,
                ))
                continue
            d = date(year, month, day)
            dates.append(get_day_status(d, checkin_dates, rest_suggested_dates, suggested_tasks_map, user.id, db))

    # 当月完成率
    days_with_checks = len(checkin_dates)
    total_days_in_month = calendar.monthrange(year, month)[1]
    monthly_completion_rate = round(days_with_checks / total_days_in_month * 100, 1) if total_days_in_month > 0 else 0.0

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
    """获取今日任务列表"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

    # 今日应完成的任务（start_date <= today，且未过期）
    active_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.status.in_(["active", "completed"]),
            Task.start_date <= today,
            (Task.end_date == None) | (Task.end_date >= today),
        )
        .all()
    )

    # 今日已打卡的任务
    today_checkins = (
        db.query(Checkin.task_id)
        .filter(
            Checkin.user_id == user.id,
            Checkin.checkin_time >= today_start,
            Checkin.checkin_time < today_end,
        )
        .all()
    )
    checked_task_ids = {c.task_id for c in today_checkins}

    tasks = []
    checkin_count = len(checked_task_ids)

    for task in active_tasks:
        tasks.append(TodayTaskItem(
            id=task.id,
            name=task.name,
            subject=task.subject or "",
            task_type=task.task_type,
            suggested_duration=task.suggested_duration,
            completed=task.id in checked_task_ids,
            is_review=task.is_review_task,
        ))

    return CalendarTodayResponse(
        date=today.isoformat(),
        tasks=tasks,
        checkin_count=checkin_count,
        total_tasks=len(tasks),
    )


@router.get("/tomorrow", response_model=CalendarTomorrowResponse)
async def get_tomorrow_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取明日推荐任务"""
    tomorrow = date.today() + timedelta(days=1)

    # 获取明天开始的活跃任务
    tomorrow_tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user.id,
            Task.status == "active",
            Task.start_date <= tomorrow,
            (Task.end_date == None) | (Task.end_date >= tomorrow),
            Task.is_review_task == False,
        )
        .all()
    )

    # 检查是否需要休息
    seven_days_ago = date.today() - timedelta(days=7)
    recent_checkins = (
        db.query(func.count(func.distinct(func.date(Checkin.checkin_time))))
        .filter(
            Checkin.user_id == user.id,
            Checkin.checkin_time >= seven_days_ago,
        )
        .scalar()
    ) or 0

    rest_suggested = recent_checkins >= 7

    recommended_tasks = []
    for task in tomorrow_tasks[:5]:  # 最多推荐 5 个
        recommended_tasks.append(TomorrowRecommendedTask(
            task_name=task.name,
            subject=task.subject or "",
            difficulty=task.difficulty,
            suggested_duration=task.suggested_duration,
            reason="明日计划任务" if not task.is_review_task else "基于遗忘曲线推荐复习",
        ))

    return CalendarTomorrowResponse(
        date=tomorrow.isoformat(),
        recommended_tasks=recommended_tasks,
        rest_suggested=rest_suggested,
        rest_reason="已连续打卡7天，建议适当休息" if rest_suggested else "",
    )
