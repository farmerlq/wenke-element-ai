"""
FastAPI依赖项
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import SecurityManager
from app.models.user import SysUser

# JWT认证方案
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> SysUser:
    """获取当前认证用户"""
    token = credentials.credentials
    return SecurityManager.get_current_user(db, token)

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> SysUser:
    """可选的当前用户（用于公开接口）"""
    try:
        token = credentials.credentials
        return SecurityManager.get_current_user(db, token)
    except HTTPException:
        return None

def get_db_session():
    """获取数据库会话"""
    return next(get_db())