from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, BigInteger, CHAR, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("sys_user.user_id"), nullable=False)
    title = Column(String(255), nullable=False)
    session_type = Column(String(50))
    ai_platform = Column(String(50))
    ai_platform_app_id = Column(String(255))
    config = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    agent_id = Column(BigInteger, nullable=False)
    ai_platform_id = Column(Integer)
    
    # 关联
    user = relationship("SysUser", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON)
    platform_response_id = Column(String(255))
    tokens_used = Column(Integer)
    processing_time = Column(Integer)
    created_at = Column(DateTime)
    
    # 关联
    session = relationship("ChatSession", back_populates="messages")