from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # 应用配置
    DEBUG: bool = False
    APP_NAME: str = "WenKe AI Backend"
    
    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./app.db",
        description="Database connection URL"
    )
    
    # Redis配置
    REDIS_URL: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # AI平台配置
    DIFY_API_KEY: str = Field(
        default="your-dify-api-key-here",
        description="Dify platform API key"
    )
    DIFY_BASE_URL: str = Field(
        default="https://api.dify.ai/v1",
        description="Dify API base URL"
    )
    
    class Config:
        env_file = ".env"

settings = Settings()