"""
排行与徽章路由
"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Task, Checkin, Badge, UserBadge, Group, UserGroup
from schemas import RankingMeResponse, BadgeOut
from typing import List
from pydantic import BaseModel
from auth import get_current_user

router = APIRouter(tags=["排行与徽章"])


def calculate_regularity_score(user_id: int, db: Session) -> float:
    """Calculate a simple MVP score from flat task completion in the last 30 days."""
    start = date.today() - timedelta(days=29)
    tasks = (
        db.query(Task)
        .filter(
            Task.user_id == user_id,
            Task.status != "deleted",
            Task.start_date >= start,
            Task.start_date <= date.today(),
        )
        .all()
    )

    if not tasks:
        return -1.0

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
    score = completed / len(tasks) * 100.0

    return round(score, 1)


def determine_rank_range(scores: list, user_score: float) -> str:
    """根据得分在所有得分中的百分位确定排名区间"""
    if user_score < 0:
        return "insufficient"

    if not scores:
        return "insufficient"

    total = len(scores)
    if total <= 1:
        return "top_20"

    higher_count = sum(1 for s in scores if s > user_score)
    rank_percentile = (higher_count + 1) / total

    if rank_percentile <= 0.2:
        return "top_20"
    elif rank_percentile <= 0.6:
        return "top_60"
    else:
        return "bottom_40"


RANK_LABELS = {
    "top_20": "前 20%",
    "top_60": "20%-60%",
    "bottom_40": "60%+",
    "insufficient": "数据不足",
}

RANK_TITLES = {
    "top_20": "规律达人",
    "top_60": "习惯养成者",
    "bottom_40": "继续加油",
    "insufficient": "打卡不足7次",
}


def get_all_user_scores(db: Session) -> dict:
    """获取所有用户的规律性得分"""
    users = db.query(User).filter(User.role == "user").all()
    scores = {}
    for u in users:
        score = calculate_regularity_score(u.id, db)
        scores[u.id] = score
    return scores


@router.get("/ranking/me", response_model=RankingMeResponse)
async def get_my_ranking(
    scope: str = Query("global", pattern="^(global|group)$"),
    group_id: int = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户排名区间"""
    user_score = calculate_regularity_score(user.id, db)

    all_scores = get_all_user_scores(db)

    if scope == "global":
        scores = [s for s in all_scores.values() if s >= 0]
        rank_range = determine_rank_range(scores, user_score)
        total_participants = len(scores)
        group_rank_range = None
    else:
        # 小组排行
        total_participants = 0
        group_rank_range = None
        rank_range = "insufficient"

        if group_id:
            # 获取小组所有成员
            member_ids = (
                db.query(UserGroup.user_id)
                .filter(UserGroup.group_id == group_id)
                .all()
            )
            member_ids = [m.user_id for m in member_ids]
            total_participants = len(member_ids)
            scores = [s for uid, s in all_scores.items() if uid in member_ids and s >= 0]
            rank_range = determine_rank_range(scores, user_score)
            group_rank_range = rank_range
        else:
            # 查找用户所在小组
            user_group = (
                db.query(UserGroup).filter(UserGroup.user_id == user.id).first()
            )
            if user_group:
                member_ids = (
                    db.query(UserGroup.user_id)
                    .filter(UserGroup.group_id == user_group.group_id)
                    .all()
                )
                member_ids = [m.user_id for m in member_ids]
                total_participants = len(member_ids)
                scores = [s for uid, s in all_scores.items() if uid in member_ids and s >= 0]
                rank_range = determine_rank_range(scores, user_score)
                group_rank_range = rank_range
            else:
                total_participants = 0

    return RankingMeResponse(
        user_id=user.id,
        regularity_score=max(0, user_score),
        rank_range=rank_range,
        rank_range_label=RANK_LABELS.get(rank_range, ""),
        rank_title=RANK_TITLES.get(rank_range, ""),
        total_participants=total_participants,
        scope=scope,
        group_id=group_id,
        group_rank_range=group_rank_range,
    )


@router.get("/badges", response_model=list[BadgeOut])
async def get_all_badges(db: Session = Depends(get_db)):
    """获取全部徽章列表"""
    badges = db.query(Badge).all()
    return [BadgeOut.model_validate(b) for b in badges]


@router.get("/badges/me", response_model=list[BadgeOut])
async def get_my_badges(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户已获得的徽章"""
    all_badges = db.query(Badge).all()
    user_badge_ids = {
        ub.badge_id
        for ub in db.query(UserBadge).filter(UserBadge.user_id == user.id).all()
    }

    result = []
    for badge in all_badges:
        earned = badge.id in user_badge_ids
        earned_at = None
        if earned:
            ub = db.query(UserBadge).filter(
                UserBadge.user_id == user.id,
                UserBadge.badge_id == badge.id,
            ).first()
            if ub:
                earned_at = ub.earned_at

        result.append(BadgeOut(
            id=badge.id,
            name=badge.name,
            description=badge.description,
            type=badge.type,
            threshold=badge.threshold,
            icon_css=badge.icon_css,
            earned=earned,
            earned_at=earned_at,
        ))

    return result


class RankingItem(BaseModel):
    """排行列表项"""
    user_id: int
    nickname: str
    regularity_score: float


class RankingListResponse(BaseModel):
    """排行列表响应"""
    scope: str
    total_participants: int
    rankings: List[RankingItem]


@router.get("/ranking/", response_model=RankingListResponse)
async def get_ranking(
    scope: str = Query("global", pattern="^(global|group)$"),
    group_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """获取排行榜列表"""
    all_scores_raw = get_all_user_scores(db)

    # 根据 scope 过滤
    if scope == "group" and group_id:
        member_ids = (
            db.query(UserGroup.user_id)
            .filter(UserGroup.group_id == group_id)
            .all()
        )
        member_ids = {m.user_id for m in member_ids}
        scores = {uid: s for uid, s in all_scores_raw.items() if uid in member_ids}
    else:
        scores = all_scores_raw

    # 只统计有效得分（>=0）
    valid_scores = {uid: s for uid, s in scores.items() if s >= 0}

    # 按得分降序排列
    sorted_users = sorted(valid_scores.items(), key=lambda x: x[1], reverse=True)

    # 获取昵称
    user_nicknames = {}
    users = db.query(User).filter(User.id.in_([uid for uid, _ in sorted_users])).all()
    for u in users:
        user_nicknames[u.id] = u.nickname

    rankings = [
        RankingItem(
            user_id=uid,
            nickname=user_nicknames.get(uid, "未知用户"),
            regularity_score=score,
        )
        for uid, score in sorted_users
    ]

    return RankingListResponse(
        scope=scope,
        total_participants=len(rankings),
        rankings=rankings,
    )
