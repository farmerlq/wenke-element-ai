from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, BigInteger, CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class SysUser(Base):
    __tablename__ = "sys_user"
    
    user_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    user_name = Column(String(30), unique=True, index=True, nullable=False)
    nick_name = Column(String(30))
    password = Column(String(100), nullable=False)
    email = Column(String(50), unique=True, index=True)
    phonenumber = Column(String(11))
    sex = Column(CHAR(1), default='2')
    avatar = Column(String(100))
    status = Column(CHAR(1), default='0')
    del_flag = Column(CHAR(1), default='0')
    login_ip = Column(String(50))
    login_date = Column(DateTime)
    create_by = Column(String(64))
    create_time = Column(DateTime, server_default=func.now())
    update_by = Column(String(64))
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now())
    remark = Column(String(500))
    
    # 关联
    sessions = relationship("ChatSession", back_populates="user")