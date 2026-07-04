"""
设置与小组路由
"""
import uuid
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Checkin, Group, UserGroup, Task, Badge, UserBadge
from schemas import (
    ReminderSettings, GroupOut, MyGroupResponse,
    CreateGroupRequest, JoinGroupRequest, UpdateGroupRequest,
    GroupMemberOut, BadgeSummary,
)
from auth import get_current_user
from routers.ranking_router import calculate_regularity_score, determine_rank_range, RANK_LABELS

router = APIRouter(tags=["设置与小组"])


def weekly_completion_rate(user_id: int, db: Session) -> float:
    today = date.today()
    start = today - timedelta(days=6)
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
        .filter(Checkin.user_id == user_id, Checkin.task_id.in_(task_ids))
        .all()
    )
    completed = {
        (row.task_id, row.checkin_date)
        for row in checkins
    }
    done = sum(1 for task in tasks if (task.id, task.start_date) in completed)
    return round(done / len(tasks) * 100, 1)


def group_member_ids(group_id: int, db: Session) -> list[int]:
    rows = db.query(UserGroup.user_id).filter(UserGroup.group_id == group_id).all()
    return [row.user_id for row in rows]


def group_completion_rate(group_id: int, db: Session) -> float:
    member_ids = group_member_ids(group_id, db)
    if not member_ids:
        return 0.0
    rates = [weekly_completion_rate(member_id, db) for member_id in member_ids]
    return round(sum(rates) / len(rates), 1) if rates else 0.0


def user_group_role(user: User, group: Group | None) -> str:
    if not group:
        return "none"
    return "owner" if group.creator_id == user.id else "member"


def group_rank_for_user(user_id: int, member_ids: list[int], db: Session) -> tuple[str, str]:
    user_score = calculate_regularity_score(user_id, db)
    scores = [
        calculate_regularity_score(member_id, db)
        for member_id in member_ids
    ]
    valid_scores = [score for score in scores if score >= 0]
    rank_range = determine_rank_range(valid_scores, user_score)
    return rank_range, RANK_LABELS.get(rank_range, "数据不足")


def user_badge_summaries(user_id: int, db: Session, limit: int = 3) -> list[BadgeSummary]:
    rows = (
        db.query(UserBadge, Badge)
        .join(Badge, Badge.id == UserBadge.badge_id)
        .filter(UserBadge.user_id == user_id)
        .order_by(UserBadge.earned_at.desc())
        .limit(limit)
        .all()
    )
    return [
        BadgeSummary(
            id=badge.id,
            name=badge.name,
            type=badge.type,
            icon_css=badge.icon_css or "",
            earned_at=user_badge.earned_at,
        )
        for user_badge, badge in rows
    ]


def build_group_out(group: Group, db: Session, include_invite: bool = False) -> GroupOut:
    member_count = (
        db.query(func.count(UserGroup.user_id))
        .filter(UserGroup.group_id == group.id)
        .scalar()
    ) or 0
    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        invite_code=group.invite_code if include_invite else "",
        creator_id=group.creator_id,
        member_count=member_count,
        completion_rate=group_completion_rate(group.id, db),
        created_at=group.created_at,
    )


def require_group_member(user: User, group_id: int, db: Session) -> Group:
    membership = (
        db.query(UserGroup)
        .filter(UserGroup.user_id == user.id, UserGroup.group_id == group_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="你不在该小组中")

    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    return group


# =============================================================================
# 提醒设置
# =============================================================================

@router.get("/settings/reminder", response_model=ReminderSettings)
async def get_reminder_settings(
    user: User = Depends(get_current_user),
):
    """获取提醒设置"""
    return ReminderSettings(
        reminder_enabled=user.reminder_enabled,
        reminder_time=user.reminder_time,
        task_expire_notify=user.task_expire_notify,
    )


@router.put("/settings/reminder", response_model=ReminderSettings)
async def update_reminder_settings(
    req: ReminderSettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新提醒设置"""
    user.reminder_enabled = req.reminder_enabled
    user.reminder_time = req.reminder_time
    user.task_expire_notify = req.task_expire_notify
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return ReminderSettings(
        reminder_enabled=user.reminder_enabled,
        reminder_time=user.reminder_time,
        task_expire_notify=user.task_expire_notify,
    )


# =============================================================================
# PDF 导出
# =============================================================================

@router.get("/report/pdf")
async def export_pdf(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成并返回用户学习报告 PDF"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF 导出功能依赖 reportlab，请安装: pip install reportlab")

    # 收集统计数据
    total_checkins = (
        db.query(func.count(Checkin.id))
        .filter(Checkin.user_id == user.id)
        .scalar()
    ) or 0

    # 生成 PDF
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 标题
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(50, height - 50, "Learning Report")
    pdf.setFont("Helvetica", 14)
    pdf.drawString(50, height - 80, f"User: {user.nickname}")
    pdf.drawString(50, height - 100, f"Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

    # 统计数据
    y = height - 150
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Statistics")

    y -= 30
    pdf.setFont("Helvetica", 14)
    pdf.drawString(50, y, f"Total checkins: {total_checkins}")
    y -= 25
    pdf.drawString(50, y, f"Learning goal: {user.learning_goal or 'Not set'}")

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=learning_report_{user.id}.pdf"
        },
    )


# =============================================================================
# 小组管理
# =============================================================================

@router.get("/groups/my", response_model=MyGroupResponse)
async def get_my_group(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的小组信息"""
    user_group = (
        db.query(UserGroup).filter(UserGroup.user_id == user.id).first()
    )

    if not user_group:
        return MyGroupResponse(group=None, my_group_role="none", my_rank_range=None, my_rank_range_label=None)

    group = db.query(Group).filter(Group.id == user_group.group_id).first()
    if not group:
        return MyGroupResponse(group=None, my_group_role="none", my_rank_range=None, my_rank_range_label=None)

    role = user_group_role(user, group)
    rank_range, rank_label = group_rank_for_user(user.id, group_member_ids(group.id, db), db)

    return MyGroupResponse(
        group=build_group_out(group, db, include_invite=role == "owner"),
        my_group_role=role,
        my_rank_range=rank_range,
        my_rank_range_label=rank_label,
    )


@router.post("/groups/", response_model=GroupOut)
async def create_group(
    req: CreateGroupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建小组 + 自动生成邀请码，创建者自动加入"""
    import random
    import string

    existing_membership = db.query(UserGroup).filter(UserGroup.user_id == user.id).first()
    if existing_membership:
        raise HTTPException(status_code=400, detail="你已加入小组，暂不支持同时加入多个小组")

    # 生成唯一邀请码（8位字母数字）
    invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    max_retries = 10
    for _ in range(max_retries):
        existing = db.query(Group).filter(Group.invite_code == invite_code).first()
        if not existing:
            break
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    else:
        raise HTTPException(status_code=500, detail="无法生成唯一邀请码，请稍后重试")

    group = Group(
        name=req.name,
        description=req.description or "",
        invite_code=invite_code,
        creator_id=user.id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)

    # 创建者自动加入小组
    user_group = UserGroup(user_id=user.id, group_id=group.id)
    db.add(user_group)
    db.commit()

    return build_group_out(group, db, include_invite=True)


@router.post("/groups/join", response_model=MyGroupResponse)
async def join_group(
    req: JoinGroupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """通过邀请码加入小组"""
    existing_membership = db.query(UserGroup).filter(UserGroup.user_id == user.id).first()
    if existing_membership:
        raise HTTPException(status_code=400, detail="你已加入小组，暂不支持同时加入多个小组")

    group = db.query(Group).filter(Group.invite_code == req.invite_code).first()
    if not group:
        raise HTTPException(status_code=404, detail="邀请码无效，未找到对应小组")

    # 检查是否已加入
    existing = (
        db.query(UserGroup)
        .filter(UserGroup.user_id == user.id, UserGroup.group_id == group.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="你已在该小组中")

    user_group = UserGroup(
        user_id=user.id,
        group_id=group.id,
    )
    db.add(user_group)
    db.commit()

    rank_range, rank_label = group_rank_for_user(user.id, group_member_ids(group.id, db), db)

    return MyGroupResponse(
        group=build_group_out(group, db, include_invite=False),
        my_group_role="member",
        my_rank_range=rank_range,
        my_rank_range_label=rank_label,
    )


@router.put("/groups/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: int,
    req: UpdateGroupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新小组信息（仅创建者）"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")

    if group.creator_id != user.id:
        raise HTTPException(status_code=403, detail="仅小组创建者可修改小组信息")

    if req.name is not None:
        group.name = req.name
    if req.description is not None:
        group.description = req.description

    db.commit()
    db.refresh(group)

    return build_group_out(group, db, include_invite=True)


@router.get("/groups/{group_id}/members", response_model=list[GroupMemberOut])
async def list_group_members(
    group_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看小组成员概览（仅小组成员可看）"""
    group = require_group_member(user, group_id, db)
    member_ids = group_member_ids(group.id, db)
    rank_scores = {
        member_id: calculate_regularity_score(member_id, db)
        for member_id in member_ids
    }
    valid_scores = [score for score in rank_scores.values() if score >= 0]

    rows = (
        db.query(UserGroup, User)
        .join(User, User.id == UserGroup.user_id)
        .filter(UserGroup.group_id == group.id)
        .order_by(UserGroup.joined_at.asc())
        .all()
    )

    result = []
    for membership, member in rows:
        rank_range = determine_rank_range(valid_scores, rank_scores.get(member.id, -1.0))
        result.append(GroupMemberOut(
            user_id=member.id,
            nickname=member.nickname or "用户",
            role="owner" if member.id == group.creator_id else "member",
            weekly_completion_rate=weekly_completion_rate(member.id, db),
            rank_range=rank_range,
            rank_range_label=RANK_LABELS.get(rank_range, "数据不足"),
            joined_at=membership.joined_at,
            badges=user_badge_summaries(member.id, db),
        ))
    return result


@router.delete("/groups/leave")
async def leave_group(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """普通成员退出小组；组长仅在无其他成员时可退出并删除小组"""
    membership = db.query(UserGroup).filter(UserGroup.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="你尚未加入小组")

    group = db.query(Group).filter(Group.id == membership.group_id).first()
    if not group:
        db.delete(membership)
        db.commit()
        return {"message": "已退出小组"}

    member_count = (
        db.query(func.count(UserGroup.user_id))
        .filter(UserGroup.group_id == group.id)
        .scalar()
    ) or 0
    if group.creator_id == user.id and member_count > 1:
        raise HTTPException(status_code=400, detail="组长需先移除其他成员后才能退出小组")

    db.delete(membership)
    if group.creator_id == user.id:
        db.delete(group)
    db.commit()
    return {"message": "已退出小组"}


@router.delete("/groups/{group_id}/members/{member_id}")
async def remove_group_member(
    group_id: int,
    member_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """组长移除小组成员"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    if group.creator_id != user.id:
        raise HTTPException(status_code=403, detail="仅组长可移除成员")
    if member_id == user.id:
        raise HTTPException(status_code=400, detail="组长不能移除自己")

    membership = (
        db.query(UserGroup)
        .filter(UserGroup.group_id == group.id, UserGroup.user_id == member_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="成员不存在")

    db.delete(membership)
    db.commit()
    return {"message": "已移除成员"}
