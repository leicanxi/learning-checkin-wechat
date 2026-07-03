"""
FastAPI 主入口
- CORS 配置
- 路由注册
- 数据库表自动创建
- 徽章初始化
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, SessionLocal, Base
from config import settings
from models import Badge  # noqa: 确保模型被 SQLAlchemy 发现

# ---------------------------------------------------------------------------
# 应用生命周期
# ---------------------------------------------------------------------------

DEFAULT_BADGES = [
    {"name": "规律达人", "description": "规律性排名进入前20%", "type": "regularity", "threshold": 0.2, "icon_css": ""},
    {"name": "习惯养成者", "description": "规律性排名进入前60%", "type": "regularity", "threshold": 0.6, "icon_css": ""},
    {"name": "进步之星", "description": "规律性得分持续提升", "type": "progress", "threshold": None, "icon_css": ""},
    {"name": "七日连续", "description": "连续打卡7天", "type": "achievement", "threshold": 7, "icon_css": ""},
    {"name": "英语坚持", "description": "英语科目打卡30次", "type": "achievement", "threshold": 30, "icon_css": ""},
    {"name": "错题复盘", "description": "完成10次复习打卡", "type": "achievement", "threshold": 10, "icon_css": ""},
    {"name": "早起学习", "description": "早上6-8点打卡20次", "type": "achievement", "threshold": 20, "icon_css": ""},
    {"name": "晚间专注", "description": "晚上19-23点打卡30次", "type": "achievement", "threshold": 30, "icon_css": ""},
    {"name": "小组贡献", "description": "小组完成率≥80%", "type": "achievement", "threshold": 0.8, "icon_css": ""},
    {"name": "新计划创建", "description": "创建首个AI学习计划", "type": "achievement", "threshold": 1, "icon_css": ""},
]


def init_badges():
    """初始化 10 个徽章到 badges 表（幂等）"""
    db = SessionLocal()
    try:
        existing_count = db.query(Badge).count()
        if existing_count == 0:
            for badge_data in DEFAULT_BADGES:
                badge = Badge(**badge_data)
                db.add(badge)
            db.commit()
            print(f"[Init] 已创建 {len(DEFAULT_BADGES)} 个徽章")
        else:
            print(f"[Init] 徽章表已有 {existing_count} 条记录，跳过初始化")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    # 启动时
    Base.metadata.create_all(bind=engine)
    init_badges()
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    print(f"[Startup] 应用已启动")
    yield
    # 关闭时
    print(f"[Shutdown] 应用已关闭")


# ---------------------------------------------------------------------------
# 创建 FastAPI 应用
# ---------------------------------------------------------------------------

app = FastAPI(
    title="学习打卡追踪器",
    description="学习打卡追踪器后端 API 服务",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - 开发阶段允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------

from routers.auth_router import router as auth_router
from routers.tasks_router import router as tasks_router
from routers.checkins_router import router as checkins_router
from routers.ai_router import router as ai_router
from routers.stats_router import router as stats_router
from routers.calendar_router import router as calendar_router
from routers.ranking_router import router as ranking_router
from routers.settings_router import router as settings_router

app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(checkins_router)
app.include_router(ai_router)
app.include_router(stats_router)
app.include_router(calendar_router)
app.include_router(ranking_router)
app.include_router(settings_router)


# ---------------------------------------------------------------------------
# 根路径健康检查
# ---------------------------------------------------------------------------

@app.get("/", tags=["健康检查"])
async def root():
    return {
        "message": "学习打卡追踪器 API 服务运行正常",
        "version": "1.0.0",
        "docs": "/docs",
    }
