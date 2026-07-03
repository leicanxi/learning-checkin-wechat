"""
统计服务路由
"""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Task, Checkin
from schemas import StatsResponse, SubjectDistribution, CheckinTrend
from auth import get_current_user

router = APIRouter(prefix="/stats", tags=["统计服务"])


def calculate_streak(user_id: int, db: Session) -> tuple:
    """计算当前连续打卡天数和最长连续天数"""
    # 获取所有打卡日期（去重）
    checkins = (
        db.query(func.date(Checkin.checkin_time).label("checkin_date"))
        .filter(Checkin.user_id == user_id)
        .group_by(func.date(Checkin.checkin_time))
        .order_by(func.date(Checkin.checkin_time).desc())
        .all()
    )

    dates = [datetime.strptime(r.checkin_date, "%Y-%m-%d").date() for r in checkins]

    if not dates:
        return 0, 0

    # 计算当前连续
    today = date.today()
    current_streak = 0
    check_date = today

    for _ in range(len(dates)):
        if check_date in dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        elif check_date - timedelta(days=1) in dates:
            # 允许一天间隔
            current_streak += 1
            check_date -= timedelta(days=1)
        elif check_date == today and (today - timedelta(days=1)) in dates:
            current_streak += 1
            check_date = today - timedelta(days=1)
        else:
            break

    # 计算最长连续
    longest = 1
    temp = 1
    sorted_dates = sorted(set(dates))
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days <= 2:
            temp += 1
        else:
            longest = max(longest, temp)
            temp = 1
    longest = max(longest, temp)

    return current_streak, longest


def calculate_completion_rate(user_id: int, days: int, db: Session) -> float:
    """计算指定天数内的打卡完成率"""
    start_date = date.today() - timedelta(days=days)

    # 该时间段应有任务的天数
    task_days = (
        db.query(func.count(func.distinct(func.date(Task.start_date))))
        .filter(
            Task.user_id == user_id,
            Task.status.in_(["active", "completed"]),
            Task.start_date >= start_date,
        )
        .scalar()
    ) or 0

    # 实际打卡天数
    checkin_days = (
        db.query(func.count(func.distinct(func.date(Checkin.checkin_time))))
        .filter(
            Checkin.user_id == user_id,
            func.date(Checkin.checkin_time) >= start_date.isoformat(),
        )
        .scalar()
    ) or 0

    if task_days == 0:
        return 0.0

    return round(checkin_days / task_days * 100, 1)


@router.get("/", response_model=StatsResponse)
async def get_stats(
    period: str = Query("week", pattern="^(week|month|year)$"),
    start: Optional[str] = Query(None, description="自定义开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="自定义结束日期 YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户统计数据"""
    # 连续天数
    current_streak, longest_streak = calculate_streak(user.id, db)

    # 打卡率
    weekly_rate = calculate_completion_rate(user.id, 7, db)
    monthly_rate = calculate_completion_rate(user.id, 30, db)

    # 总打卡次数
    total_checkins = (
        db.query(func.count(Checkin.id))
        .filter(Checkin.user_id == user.id)
        .scalar()
    ) or 0

    # 科目分布
    subject_rows = (
        db.query(Checkin.subject, func.count(Checkin.id).label("cnt"))
        .filter(Checkin.user_id == user.id, Checkin.subject != "")
        .group_by(Checkin.subject)
        .order_by(func.count(Checkin.id).desc())
        .all()
    )

    subject_distribution = []
    for row in subject_rows:
        pct = round(row.cnt / total_checkins * 100, 1) if total_checkins > 0 else 0.0
        subject_distribution.append(
            SubjectDistribution(subject=row.subject, count=row.cnt, percentage=pct)
        )

    # 打卡趋势
    days_lookup = {"week": 7, "month": 30, "year": 365}
    trend_days = days_lookup.get(period, 7)

    if start and end:
        trend_start = datetime.strptime(start, "%Y-%m-%d")
        trend_end = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
    else:
        trend_end = datetime.utcnow()
        trend_start = trend_end - timedelta(days=trend_days)

    trend_rows = (
        db.query(
            func.date(Checkin.checkin_time).label("d"),
            func.count(Checkin.id).label("cnt"),
        )
        .filter(
            Checkin.user_id == user.id,
            Checkin.checkin_time >= trend_start,
            Checkin.checkin_time < trend_end,
        )
        .group_by(func.date(Checkin.checkin_time))
        .order_by(func.date(Checkin.checkin_time))
        .all()
    )

    checkin_trend = [
        CheckinTrend(date=row.d, count=row.cnt) for row in trend_rows
    ]

    # 知识进度（简化版）
    knowledge_progress = {
        "learning": 40,
        "reviewing": 30,
        "mastered": 30,
    }

    # 预估剩余天数
    active_tasks = (
        db.query(func.count(Task.id))
        .filter(Task.user_id == user.id, Task.status == "active")
        .scalar()
    ) or 0
    estimated_remaining_days = active_tasks * 7

    return StatsResponse(
        current_streak=current_streak,
        longest_streak=longest_streak,
        weekly_rate=weekly_rate,
        monthly_rate=monthly_rate,
        total_checkins=total_checkins,
        knowledge_progress=knowledge_progress,
        subject_distribution=subject_distribution,
        checkin_trend=checkin_trend,
        estimated_remaining_days=estimated_remaining_days,
    )
