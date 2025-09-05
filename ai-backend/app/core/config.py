from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "yjakgl11"
    DB_NAME: str = "ai_chat"
    DB_CHARSET: str = "utf8mb4"
    
    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True
    
    # AI平台默认配置
    DEFAULT_DIFY_BASE_URL: str = "https://api.dify.dev/v1"
    DEFAULT_COZE_BASE_URL: str = "https://api.coze.cn/open_api/v2"
    DEFAULT_N8N_BASE_URL: str = "https://your-n8n-instance.com/webhook"
    
    class Config:
        env_file = ".env"

settings = Settings()