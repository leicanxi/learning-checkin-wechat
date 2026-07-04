"""
数据库模型定义（7张表）
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time,
    Text, Float, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(64), unique=True, nullable=True)
    nickname = Column(String(100), default="")
    avatar = Column(String(500), default="")
    learning_goal = Column(String(200), default="")
    role = Column(String(10), default="user")
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    timezone = Column(String(50), default="Asia/Shanghai")
    reminder_enabled = Column(Boolean, default=False)
    reminder_time = Column(Time, default=lambda: datetime.strptime("21:00:00", "%H:%M:%S").time())
    task_expire_notify = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tasks = relationship("Task", back_populates="user", foreign_keys="Task.user_id")
    checkins = relationship("Checkin", back_populates="user")
    user_groups = relationship("UserGroup", back_populates="user")
    user_badges = relationship("UserBadge", back_populates="user")
    created_groups = relationship("Group", back_populates="creator", foreign_keys="Group.creator_id")


class Task(Base):
    """打卡任务表"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(200), default="")
    subject = Column(String(50), default="")
    suggested_duration = Column(Integer, default=25)
    task_type = Column(String(20), default="main")
    repeat_days = Column(Integer, default=127)
    difficulty = Column(String(10), default="medium")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), default="active")
    is_ai_generated = Column(Boolean, default=False)
    is_review_task = Column(Boolean, default=False)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    ai_review_intervals = Column(Text, nullable=True)  # JSON 数组字符串
    knowledge_tags = Column(Text, nullable=True)
    source = Column(String(20), default="manual")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="tasks", foreign_keys=[user_id])
    checkins = relationship("Checkin", back_populates="task")
    parent_task = relationship("Task", remote_side=[id], backref="child_review_tasks")


class Checkin(Base):
    """打卡记录表"""
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    subject = Column(String(50), default="")
    checkin_date = Column(Date, nullable=True)
    checkin_time = Column(DateTime, nullable=False)
    is_review = Column(Boolean, default=False)
    review_round = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 复合唯一约束: 同一用户同一任务同一天只能有一条打卡记录
    __table_args__ = (
        UniqueConstraint("user_id", "task_id", "checkin_date", name="uq_user_task_checkin_date"),
        Index("idx_checkin_user_date", "user_id", "checkin_date"),
    )

    # 关系
    user = relationship("User", back_populates="checkins")
    task = relationship("Task", back_populates="checkins")


class Group(Base):
    """小组表"""
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    invite_code = Column(String(20), unique=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    creator = relationship("User", back_populates="created_groups", foreign_keys=[creator_id])
    user_groups = relationship("UserGroup", back_populates="group")


class UserGroup(Base):
    """用户-小组关联表"""
    __tablename__ = "user_groups"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="user_groups")
    group = relationship("Group", back_populates="user_groups")


class Badge(Base):
    """徽章表"""
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    description = Column(String(200), default="")
    type = Column(String(20), nullable=False)  # regularity / progress / achievement
    threshold = Column(Float, nullable=True)
    icon_css = Column(String(500), default="")

    # 关系
    user_badges = relationship("UserBadge", back_populates="badge")


class UserBadge(Base):
    """用户-徽章关联表"""
    __tablename__ = "user_badges"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    badge_id = Column(Integer, ForeignKey("badges.id"), primary_key=True)
    earned_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="user_badges")
    badge = relationship("Badge", back_populates="user_badges")
