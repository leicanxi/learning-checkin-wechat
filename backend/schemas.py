"""
Pydantic 请求/响应模型
"""
from datetime import date, datetime, time
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# 通用
# =============================================================================

class ResponseBase(BaseModel):
    """通用响应"""
    code: int = 200
    message: str = "ok"
    data: Any = None


# =============================================================================
# 用户认证
# =============================================================================

class WechatLoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="wx.login() 返回的临时 code")


class EmailRegisterRequest(BaseModel):
    """邮箱注册请求"""
    nickname: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=50)


class EmailLoginRequest(BaseModel):
    """邮箱登录请求"""
    email: EmailStr
    password: str


class UpdateUserRequest(BaseModel):
    """更新用户信息请求"""
    nickname: Optional[str] = Field(None, max_length=100)
    learning_goal: Optional[str] = Field(None, max_length=200)
    avatar: Optional[str] = Field(None, max_length=500)


class UserOut(BaseModel):
    """用户响应"""
    id: int
    openid: Optional[str] = None
    nickname: str
    avatar: str
    learning_goal: str
    role: str
    email: Optional[str] = None
    timezone: str
    reminder_enabled: bool
    reminder_time: Optional[time] = None
    task_expire_notify: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT 令牌响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# =============================================================================
# 任务管理
# =============================================================================

class TaskCreate(BaseModel):
    """创建任务请求"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    subject: Optional[str] = Field(None, max_length=50)
    suggested_duration: Optional[int] = Field(25, ge=0)
    difficulty: Optional[str] = Field("medium", pattern="^(low|medium|high)$")
    task_date: date
    knowledge_tags: List[str] = []
    source: Optional[str] = Field("manual", pattern="^(manual|ai|system)$")


class TaskBatchCreate(BaseModel):
    """批量创建任务请求"""
    tasks: List[TaskCreate]


class TaskUpdate(BaseModel):
    """更新任务请求"""
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    subject: Optional[str] = Field(None, max_length=50)
    suggested_duration: Optional[int] = Field(None, ge=0)
    difficulty: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    task_date: Optional[date] = None
    knowledge_tags: Optional[List[str]] = None
    source: Optional[str] = Field(None, pattern="^(manual|ai|system)$")
    status: Optional[str] = Field(None, pattern="^(active|expired|deleted)$")


class TaskOut(BaseModel):
    """任务响应"""
    id: int
    user_id: int
    name: str
    description: str
    subject: str
    suggested_duration: int
    difficulty: str
    task_date: date
    knowledge_tags: List[str] = []
    source: str = "manual"
    status: str
    completed: bool = False
    checkin_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskBatchOut(BaseModel):
    """批量创建任务响应"""
    created_count: int
    tasks: List[TaskOut]


# =============================================================================
# 打卡记录
# =============================================================================

class CheckinCreate(BaseModel):
    """打卡请求"""
    task_id: int
    checkin_time: Optional[datetime] = None


class CheckinBackfill(BaseModel):
    """补打卡请求"""
    task_id: int
    checkin_date: date = Field(..., description="补打卡日期，YYYY-MM-DD，必须是最近7天内")


class CheckinUpdate(BaseModel):
    """更新打卡记录请求"""
    checkin_time: Optional[datetime] = None
    subject: Optional[str] = Field(None, max_length=50)


class CheckinOut(BaseModel):
    """打卡记录响应"""
    id: int
    user_id: int
    task_id: int
    subject: str
    checkin_date: date
    checkin_time: datetime
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# AI 服务
# =============================================================================

class AIGeneratePlanRequest(BaseModel):
    """AI 生成学习计划请求"""
    content: str = Field(..., min_length=1, description="学习材料或目标描述")
    mode: Optional[str] = Field(None, pattern="^(exam|daily|skill|review|free)$")
    target_days: Optional[int] = Field(None, ge=1, le=365)


class AIPlanTask(BaseModel):
    """AI 计划中的单个子任务"""
    name: str
    task_date: date
    subject: str = ""
    suggested_duration: int = 25
    difficulty: str = "medium"
    knowledge_tags: List[str] = []
    source: str = "ai"


class AIGeneratePlanResponse(BaseModel):
    """AI 生成学习计划响应"""
    mode: str
    mode_inferred: bool = False
    total_days: int
    summary: str
    tasks: List[AIPlanTask]


class AIProgressResponse(BaseModel):
    """AI 预估进度响应"""
    knowledge_progress: dict = {}
    estimated_remaining_days: int = 0
    suggestion: str = ""


# =============================================================================
# 统计服务
# =============================================================================

class SubjectDistribution(BaseModel):
    """科目分布"""
    subject: str
    count: int
    percentage: float


class CheckinTrend(BaseModel):
    """打卡趋势"""
    date: str
    count: int


class StatsResponse(BaseModel):
    """统计数据响应"""
    current_streak: int = 0
    longest_streak: int = 0
    weekly_rate: float = 0.0
    monthly_rate: float = 0.0
    total_checkins: int = 0
    knowledge_progress: dict = {}
    subject_distribution: List[SubjectDistribution] = []
    checkin_trend: List[CheckinTrend] = []
    estimated_remaining_days: int = 0


# =============================================================================
# 排行与徽章
# =============================================================================

class RankingMeResponse(BaseModel):
    """个人排名响应"""
    user_id: int
    regularity_score: float = 0.0
    rank_range: str = "insufficient"  # top_20 / top_60 / bottom_40 / insufficient
    rank_range_label: str = ""
    rank_title: str = ""
    total_participants: int = 0
    scope: str = "global"
    group_id: Optional[int] = None
    group_rank_range: Optional[str] = None


class BadgeOut(BaseModel):
    """徽章响应"""
    id: int
    name: str
    description: str
    type: str
    threshold: Optional[float] = None
    icon_css: str
    earned: bool = False
    earned_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# =============================================================================
# 日历服务
# =============================================================================

class CalendarDate(BaseModel):
    """日历日期信息"""
    date: str
    day_of_week: int
    status: str  # checked_in / pending / missed / empty
    checkin_count: int = 0
    is_today: bool = False
    is_rest_suggested: bool = False
    suggested_tasks_preview: Optional[List[str]] = None


class CalendarMonthResponse(BaseModel):
    """日历月视图响应"""
    year: int
    month: int
    monthly_completion_rate: float = 0.0
    dates: List[CalendarDate] = []


class TodayTaskItem(BaseModel):
    """今日任务项"""
    id: int
    name: str
    task_date: date
    subject: str
    suggested_duration: int
    difficulty: str
    knowledge_tags: List[str] = []
    source: str = "manual"
    completed: bool
    checkin_id: Optional[int] = None


class CalendarTodayResponse(BaseModel):
    """今日任务响应"""
    date: str
    tasks: List[TodayTaskItem] = []
    checkin_count: int = 0
    total_tasks: int = 0


class TomorrowRecommendedTask(BaseModel):
    """明日推荐任务"""
    name: str
    task_date: date
    subject: str
    difficulty: str
    suggested_duration: int
    reason: str = ""


class CalendarTomorrowResponse(BaseModel):
    """明日推荐响应"""
    date: str
    recommended_tasks: List[TomorrowRecommendedTask] = []
    rest_suggested: bool = False
    rest_reason: str = ""


# =============================================================================
# 设置服务
# =============================================================================

class ReminderSettings(BaseModel):
    """提醒设置"""
    reminder_enabled: bool = False
    reminder_time: time = time(21, 0, 0)
    task_expire_notify: bool = True


class GroupOut(BaseModel):
    """小组响应"""
    id: int
    name: str
    description: str
    invite_code: str
    creator_id: int
    member_count: int = 0
    completion_rate: float = 0.0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MyGroupResponse(BaseModel):
    """我的小组响应"""
    group: Optional[GroupOut] = None
    my_rank_range: Optional[str] = None


class CreateGroupRequest(BaseModel):
    """创建小组请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class JoinGroupRequest(BaseModel):
    """加入小组请求"""
    invite_code: str = Field(..., max_length=20)


class UpdateGroupRequest(BaseModel):
    """更新小组请求"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
