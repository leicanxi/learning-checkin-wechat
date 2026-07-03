"""
AI 服务路由
"""
import json
import re
import httpx
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Task
from schemas import (
    AIGeneratePlanRequest, AIGeneratePlanResponse, AIPlanTask,
    AIProgressResponse,
)
from auth import get_current_user
from config import settings

router = APIRouter(prefix="/ai", tags=["AI 服务"])

# AI 调用频率限制：每用户每日 10 次
AI_DAILY_LIMIT = 10


def check_ai_rate_limit(user: User, db: Session) -> None:
    """检查用户今日 AI 调用次数，超过限制抛出 429"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_calls = (
        db.query(func.count(Task.id))
        .filter(
            Task.user_id == user.id,
            Task.is_ai_generated == True,
            Task.created_at >= today_start,
        )
        .scalar()
    ) or 0

    if today_calls >= AI_DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="今日 AI 规划次数已用完（每日 10 次），请明天再试",
        )


# =============================================================================
# 模式推断
# =============================================================================

MODE_KEYWORDS = {
    "exam": ["冲刺", "倒计时", "仅剩", "考试", "deadline"],
    "daily": ["长期", "积累", "每天一点点", "坚持", "日常"],
    "skill": ["技能", "入门到精通", "进阶", "掌握"],
    "review": ["错题", "复盘", "回顾", "查漏补缺"],
}


def infer_mode(content: str) -> str:
    """从内容中 NLP 推断学习模式，无匹配返回 'free'"""
    for mode, keywords in MODE_KEYWORDS.items():
        for kw in keywords:
            if kw in content:
                return mode
    return "free"


# =============================================================================
# Prompt 策略
# =============================================================================

MODE_PROMPTS = {
    "exam": """
你是一个考试冲刺规划师。用户在{target_days}天内需要完成备考。
请将学习材料拆解为子任务，每天安排1-3个子任务，严格在{target_days}天内排满，每个子任务必须指定 scheduled_date。
""",
    "daily": """
你是日常积累规划师。用户希望长期学习，请将材料拆解为子任务，不必每天排任务，合理安排频率（如隔天、每周3次），注重新学和复习交替。
每个子任务必须指定 scheduled_date。
""",
    "skill": """
你是技能进修规划师。请将学习路径分为基础→进阶→实战阶段，各阶段分配合理的子任务和日期，任务难度逐步提升。
每个子任务必须指定 scheduled_date。
""",
    "review": """
你是错题复盘规划师。请按艾宾浩斯遗忘曲线安排复盘节奏（间隔1/2/4/7/15天），每个错题集安排多轮复盘作为独立子任务。
所有子任务的 review_round 固定为 0（实际复习轮次的 review_round 由系统遗忘曲线服务自动管理）。
每个子任务必须指定 scheduled_date。
""",
    "free": """
请综合分析学习材料的难度、内容量和用户描述，自主决定最佳排期策略。
每个子任务必须指定 scheduled_date。
""",
}

SYSTEM_PROMPT = """
你是一个专业的学习规划师。请严格按照 JSON 格式输出：

{
  "summary": "计划概述，一句话说明规划思路",
  "plan": [
    {
      "task_name": "子任务名称",
      "scheduled_date": "YYYY-MM-DD",
      "day_number": 1,
      "subject": "科目标签",
      "suggested_duration": 25,
      "difficulty": "medium",
      "knowledge_tags": ["标签1", "标签2"],
      "review_round": 0
    }
  ]
}

注意事项：
1. scheduled_date 必须在今天到未来365天之间，YYYY-MM-DD 格式
2. day_number 从 1 开始递增
3. subject 从内容中提取，如"英语""数学""编程"等
4. suggested_duration 单位是分钟，默认25
5. difficulty 必须是 low / medium / high 之一
6. knowledge_tags 是对该子任务的知识点标记
7. review_round 固定为 0
8. 输出必须是合法 JSON，不含 markdown 代码块标记，不要用 ```json``` 包裹
9. 不要输出 JSON 之外的任何文字
"""


def parse_ai_response(text: str) -> dict:
    """解析 AI 响应，处理各种格式"""
    # 去除 markdown 代码块标记
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    # 尝试查找 JSON 对象
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        text = match.group(0)
    return json.loads(text)


async def call_deepseek(prompt: str, max_retries: int = 3) -> dict:
    """调用 DeepSeek API，带重试机制"""
    url = f"{settings.DEEPSEEK_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    temperature = 0.7
    last_error = None

    for attempt in range(max_retries):
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": 4096,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return parse_ai_response(content)
        except httpx.TimeoutException:
            last_error = "AI 服务响应超时"
        except httpx.HTTPError as e:
            last_error = f"AI 服务请求失败: {str(e)}"
        except (json.JSONDecodeError, KeyError) as e:
            # JSON 解析失败，调整 prompt 强调格式并重试
            last_error = f"AI 返回格式异常: {str(e)}"
            temperature = max(0.3, temperature - 0.2)

    raise HTTPException(status_code=500, detail=f"AI 规划暂时不可用: {last_error}")


# =============================================================================
# 路由
# =============================================================================

@router.post("/generate-plan", response_model=AIGeneratePlanResponse)
async def generate_plan(
    req: AIGeneratePlanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI 生成学习计划
    根据学习模式（或从 content 推断）调用 DeepSeek API 生成结构化任务列表
    """
    # 0. 检查每日调用次数限制
    check_ai_rate_limit(user, db)

    # 1. 确定模式
    mode = req.mode or infer_mode(req.content)
    mode_inferred = not req.mode

    if mode not in MODE_PROMPTS:
        mode = "free"

    # 2. 确定目标天数
    target_days = req.target_days or 30

    # 3. 组装 Prompt
    mode_prompt = MODE_PROMPTS[mode].format(target_days=target_days)
    user_prompt = f"""
{mode_prompt}

学习材料/目标描述：
{req.content}

计划总天数：{target_days} 天（从今天 {date.today().strftime('%Y-%m-%d')} 开始排期）
"""

    # 4. 调用 DeepSeek
    ai_result = await call_deepseek(user_prompt)

    # 5. 校验日期范围
    today = date.today()
    max_date = today + timedelta(days=365)
    valid_plan = []

    plan_data = ai_result.get("plan", [])
    for item in plan_data:
        try:
            scheduled = datetime.strptime(item["scheduled_date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue

        if today <= scheduled <= max_date:
            valid_plan.append(AIPlanTask(
                task_name=item.get("task_name", "未命名任务"),
                scheduled_date=scheduled,
                day_number=item.get("day_number", 0),
                subject=item.get("subject", ""),
                suggested_duration=item.get("suggested_duration", 25),
                difficulty=item.get("difficulty", "medium"),
                knowledge_tags=item.get("knowledge_tags", []),
                review_round=0,
            ))

    if not valid_plan:
        raise HTTPException(
            status_code=422,
            detail="AI 无法生成有效的日期计划，请调整输入内容后重试",
        )

    total_days = max(p.day_number for p in valid_plan) if valid_plan else target_days

    return AIGeneratePlanResponse(
        mode=mode,
        mode_inferred=mode_inferred,
        total_days=total_days,
        summary=ai_result.get("summary", ""),
        plan=valid_plan,
    )


@router.post("/upload-material")
async def upload_material(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    上传学习材料文件（图片/文档），供 AI 分析
    """
    import os
    import uuid

    ext = os.path.splitext(file.filename or "material.txt")[1]
    filename = f"material_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "materials")
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    contents = await file.read()

    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制")

    with open(filepath, "wb") as f:
        f.write(contents)

    return {
        "message": "文件上传成功",
        "filename": filename,
        "filepath": f"/uploads/materials/{filename}",
    }


@router.get("/progress", response_model=AIProgressResponse)
async def get_ai_progress(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取 AI 预估学习进度"""
    from sqlalchemy import func
    from models import Checkin

    # 获取用户的总任务数和打卡数
    active_tasks = db.query(Task).filter(
        Task.user_id == user.id,
        Task.status.in_(["active", "completed"]),
    ).count()

    total_checkins = db.query(Checkin).filter(
        Checkin.user_id == user.id,
    ).count()

    # 简单预估
    estimated_remaining_days = max(0, active_tasks * 7 - total_checkins) if active_tasks > 0 else 0

    knowledge_progress = {
        "learning": max(10, active_tasks * 10),
        "reviewing": max(5, total_checkins * 2),
        "mastered": max(0, min(30, total_checkins * 3)),
    }

    return AIProgressResponse(
        knowledge_progress=knowledge_progress,
        estimated_remaining_days=estimated_remaining_days,
        suggestion="继续保持学习节奏!" if total_checkins > 0 else "开始你的第一个打卡吧!",
    )
