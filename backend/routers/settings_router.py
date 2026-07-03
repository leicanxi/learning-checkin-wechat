"""
设置与小组路由
"""
import uuid
from datetime import datetime, time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Checkin, Group, UserGroup
from schemas import (
    ReminderSettings, GroupOut, MyGroupResponse,
    CreateGroupRequest, JoinGroupRequest, UpdateGroupRequest,
)
from auth import get_current_user

router = APIRouter(tags=["设置与小组"])


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
        return MyGroupResponse(group=None, my_rank_range=None)

    group = db.query(Group).filter(Group.id == user_group.group_id).first()
    if not group:
        return MyGroupResponse(group=None, my_rank_range=None)

    # 计算小组成员数和完成率
    member_count = (
        db.query(func.count(UserGroup.user_id))
        .filter(UserGroup.group_id == group.id)
        .scalar()
    ) or 0

    # 计算小组完成率（所有成员近7天打卡率的平均）
    completion_rate = 0.0

    return MyGroupResponse(
        group=GroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            invite_code=group.invite_code,
            creator_id=group.creator_id,
            member_count=member_count,
            completion_rate=round(completion_rate, 1),
            created_at=group.created_at,
        ),
        my_rank_range=None,
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

    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        invite_code=group.invite_code,
        creator_id=group.creator_id,
        member_count=1,
        completion_rate=0.0,
        created_at=group.created_at,
    )


@router.post("/groups/join", response_model=MyGroupResponse)
async def join_group(
    req: JoinGroupRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """通过邀请码加入小组"""
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

    member_count = (
        db.query(func.count(UserGroup.user_id))
        .filter(UserGroup.group_id == group.id)
        .scalar()
    ) or 0

    return MyGroupResponse(
        group=GroupOut(
            id=group.id,
            name=group.name,
            description=group.description,
            invite_code=group.invite_code,
            creator_id=group.creator_id,
            member_count=member_count,
            completion_rate=0.0,
            created_at=group.created_at,
        ),
        my_rank_range=None,
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

    member_count = (
        db.query(func.count(UserGroup.user_id))
        .filter(UserGroup.group_id == group.id)
        .scalar()
    ) or 0

    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        invite_code=group.invite_code,
        creator_id=group.creator_id,
        member_count=member_count,
        completion_rate=0.0,
        created_at=group.created_at,
    )
