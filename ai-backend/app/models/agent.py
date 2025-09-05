from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class AiPlatformType(Base):
    __tablename__ = "ai_platform_type"
    
    platform_type = Column(String(20), primary_key=True)
    platform_name = Column(String(50), nullable=False)
    description = Column(Text)

class AiAgentConfig(Base):
    __tablename__ = "ai_agent_config"
    
    agent_id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    platform_type = Column(String(20), nullable=False)
    agent_key = Column(String(100))
    description = Column(Text)
    base_url = Column(String(255), nullable=False)
    api_key = Column(String(255), nullable=False)
    access_token = Column(String(255))
    bot_id = Column(String(100))
    webhook_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    is_stream = Column(Boolean, default=True)
    user_id = Column(BigInteger)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())