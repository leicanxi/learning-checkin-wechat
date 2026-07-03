"""
JWT 认证工具
"""
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User

# Bearer Token 提取
security = HTTPBearer()


def hash_password(password: str) -> str:
    """对密码进行 SHA256 + salt 哈希"""
    salt = os.urandom(32).hex()
    hash_val = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hash_val}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希密码"""
    try:
        salt, hash_val = hashed_password.split("$", 1)
        return hashlib.sha256((plain_password + salt).encode()).hexdigest() == hash_val
    except (ValueError, AttributeError):
        return False


def create_access_token(data: dict) -> str:
    """创建 JWT 访问令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """解析 JWT 令牌，返回 payload 或 None"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    从请求 Header 中提取 Bearer token，解析 JWT 并返回当前用户。
    所有需要登录的接口依赖此函数。
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌或令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户标识",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """管理员权限检查（预留中间件，MVP 阶段不挂载到任何路由）"""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
