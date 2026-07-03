"""
环境变量配置模块
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """应用配置"""

    # 数据库
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./learning_tracker.db")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # 微信
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "wx_test_appid")
    WECHAT_APPSECRET: str = os.getenv("WECHAT_APPSECRET", "test_appsecret")

    # DeepSeek AI
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "sk-test-key")
    DEEPSEEK_API_BASE: str = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")

    # 文件上传
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB


settings = Settings()
