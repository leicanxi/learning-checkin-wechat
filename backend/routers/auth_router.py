"""
用户认证路由
"""
import httpx
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select

from database import get_db
from models import User
from schemas import (
    WechatLoginRequest, EmailRegisterRequest, EmailLoginRequest,
    UpdateUserRequest, UserOut, TokenResponse,
)
from auth import hash_password, verify_password, create_access_token, get_current_user
from config import settings

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/wechat-login", response_model=TokenResponse)
async def wechat_login(req: WechatLoginRequest, db: Session = Depends(get_db)):
    """
    微信小程序登录：
    1. 接收 wx.login() 获取的临时 code
    2. 调用微信 code2Session 换取 openid
    3. 查找或创建用户
    4. 返回 JWT token
    """
    # 调用微信 code2Session
    wechat_url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APPID,
        "secret": settings.WECHAT_APPSECRET,
        "js_code": req.code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(wechat_url, params=params)
        data = resp.json()

    openid = data.get("openid")
    if not openid:
        error_msg = data.get("errmsg", "微信登录失败")
        raise HTTPException(status_code=400, detail=f"微信登录失败: {error_msg}")

    # 查找或创建用户
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(
            openid=openid,
            nickname=f"用户{openid[-6:]}",
            role="user",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 生成 JWT
    access_token = create_access_token({
        "user_id": user.id,
        "openid": user.openid,
        "role": user.role,
    })

    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse)
async def email_register(req: EmailRegisterRequest, db: Session = Depends(get_db)):
    """
    邮箱注册（开发调试备选）
    """
    # 检查邮箱唯一性
    existing_email = db.query(User).filter(User.email == req.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = User(
        nickname=req.nickname,
        email=req.email,
        password_hash=hash_password(req.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({
        "user_id": user.id,
        "openid": user.openid or "",
        "role": user.role,
    })

    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def email_login(req: EmailLoginRequest, db: Session = Depends(get_db)):
    """
    邮箱登录（开发调试备选）
    """
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    if not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    access_token = create_access_token({
        "user_id": user.id,
        "openid": user.openid or "",
        "role": user.role,
    })

    return TokenResponse(
        access_token=access_token,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserOut.model_validate(user)


@router.put("/me", response_model=UserOut)
async def update_me(
    req: UpdateUserRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户信息（昵称、学习目标、头像）"""
    if req.nickname is not None:
        user.nickname = req.nickname
    if req.learning_goal is not None:
        user.learning_goal = req.learning_goal
    if req.avatar is not None:
        user.avatar = req.avatar

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    上传用户头像（最大 2MB）
    """
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片格式")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像文件不能超过 2MB")

    import os
    import uuid

    ext = os.path.splitext(file.filename or "avatar.png")[1] or ".png"
    filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    user.avatar = f"/uploads/avatars/{filename}"
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
