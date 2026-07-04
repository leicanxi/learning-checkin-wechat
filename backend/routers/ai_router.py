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
# Prompt 策略
# =============================================================================

MODE_PROMPTS = {
    "exam": """
你是考试冲刺规划师。请分析用户输入，自行确定考试日期和准备周期，精确安排每天的学习任务。
每天 1-3 个子任务，均匀分配学习材料。考试当天不安排任务。
""",
    "daily": """
你是日常积累规划师。不必每天排任务，合理安排频率（隔天、每周 3-4 次），注重新学和复习交替。
""",
    "skill": """
你是技能进修规划师。将学习路径分为基础→进阶→实战阶段，各阶段分配合理任务，难度逐步提升。
""",
    "review": """
你是错题复盘规划师。按艾宾浩斯遗忘曲线安排复盘节奏，每个错题集安排多轮复盘。
所有子任务的 review_round 固定为 0。
""",
    "free": """
请综合分析学习材料，自主决定最佳排期策略。同一天可以安排多个子任务，自由跳过休息日。
""",
}

SYSTEM_PROMPT = """
你是一个专业的学习规划师。用户会用自然语言描述学习目标、考试日期、学习材料。

请你自己完成以下全部工作，不需要系统辅助：
1. 理解用户的自然语言，提取考试/目标日期（如"七天后"=今天+7天，"三个月后"=今天+90天，"7月10日"=具体日期）
2. 确定准备周期（从今天到目标日期前一天）
3. 提取所有学习材料、科目、章节
4. 制定排期策略：
   - 短周期（≤14天）：按天精细排期
   - 长周期（>14天）：按周粒度排期，每周挑几天即可
5. 考试/目标当天不安排任务
6. 同一天可以有多个子任务，day_number 相同

必须严格按以下 JSON 格式输出，不要输出任何其他文字：

{
  "summary": "一句话概述整个计划",
  "plan": [
    {
      "task_name": "具体可执行的任务名称",
      "scheduled_date": "YYYY-MM-DD",
      "day_number": 1,
      "subject": "科目标签",
      "suggested_duration": 30,
      "difficulty": "medium",
      "knowledge_tags": ["标签"],
      "review_round": 0
    }
  ]
}

规则：
- scheduled_date 必须在今天到未来365天之间
- day_number 从 1 递增，同一天任务共享相同 day_number
- subject 从材料中提取
- suggested_duration 单位分钟，根据任务量合理估计
- difficulty: low / medium / high
- knowledge_tags 标注知识点
- 输出纯 JSON，不含 markdown 代码块标记
- 不要输出 JSON 之外的任何文字
"""


def parse_ai_response(text: str) -> dict:
    """解析 AI 响应，处理各种格式，含降级容错"""
    # 去除 markdown 代码块标记
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    # 尝试查找 JSON 对象
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 降级：从文本中正则提取任务列表
    print("[AI] JSON parse failed, falling back to regex extraction", flush=True)
    plan = []
    summary = ""
    # 提取 summary
    sm = re.search(r'"summary"\s*:\s*"([^"]*)"', text)
    if sm:
        summary = sm.group(1)
    # 提取 plan 数组中的每个任务
    task_blocks = re.findall(r'\{\s*"task_name"\s*:\s*"([^"]*)".*?"scheduled_date"\s*:\s*"([^"]*)".*?"suggested_duration"\s*:\s*(\d+)', text)
    if not task_blocks:
        # 更宽松的匹配
        task_blocks = re.findall(r'"task_name"\s*:\s*"([^"]*)"[^}]*"scheduled_date"\s*:\s*"(\d{4}-\d{2}-\d{2})"', text)
    for i, block in enumerate(task_blocks):
        task = {
            "task_name": block[0],
            "scheduled_date": block[1],
            "day_number": i + 1,
            "subject": "",
            "suggested_duration": int(block[2]) if len(block) > 2 else 25,
            "difficulty": "medium",
            "knowledge_tags": [],
            "review_round": 0,
        }
        plan.append(task)
    if not plan:
        raise json.JSONDecodeError("Unable to extract any tasks from AI response", text, 0)
    return {"summary": summary, "plan": plan}


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
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    print(f"[AI] HTTP {resp.status_code}: {resp.text[:500]}", flush=True)
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return parse_ai_response(content)
        except httpx.TimeoutException:
            last_error = "AI 服务响应超时"
            print(f"[AI] Timeout (attempt {attempt+1}/{max_retries})", flush=True)
        except httpx.HTTPError as e:
            last_error = f"AI 服务请求失败: {str(e)}"
            print(f"[AI] HTTP error (attempt {attempt+1}/{max_retries}): {e}", flush=True)
        except (json.JSONDecodeError, KeyError) as e:
            # JSON 解析失败，调整 prompt 强调格式并重试
            last_error = f"AI 返回格式异常: {str(e)}"
            print(f"[AI] Parse error (attempt {attempt+1}/{max_retries}): {e}", flush=True)
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
    将用户自然语言直接提交给 AI，由 AI 自主完成语义理解和任务拆解
    """
    # 0. 检查每日调用次数限制
    check_ai_rate_limit(user, db)

    # 1. 模式由前端选择器传入，后端不做推断
    mode = req.mode or "free"
    if mode not in MODE_PROMPTS:
        mode = "free"

    # 2. 组装 Prompt：只告诉 AI 今天日期和模式提示，其余全部由 AI 自己理解
    mode_prompt = MODE_PROMPTS[mode]
    today_str = date.today().strftime('%Y-%m-%d')
    user_prompt = f"""
{mode_prompt}

学习材料/目标描述：
{req.content}

注意：今天是 {today_str}，请基于今天规划所有任务的日期。
"""

    # 3. 调用 DeepSeek
    ai_result = await call_deepseek(user_prompt)

    # 4. 校验日期范围：今天 ~ 未来365天
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

    total_days = max(p.day_number for p in valid_plan) if valid_plan else 0

    return AIGeneratePlanResponse(
        mode=mode,
        mode_inferred=False,
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
