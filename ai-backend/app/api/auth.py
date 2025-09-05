from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import LoginDTO, RegisterDTO, EmailCodeDTO, BaseResponse
from app.core.dependencies import get_current_user
from app.models.user import SysUser

router = APIRouter(prefix="/auth", tags=["认证管理"])

@router.post("/login", response_model=BaseResponse)
async def login(login_dto: LoginDTO, db: Session = Depends(get_db)):
    """用户登录"""
    auth_service = AuthService(db)
    return auth_service.login(login_dto)

@router.post("/register", response_model=BaseResponse)
async def register(register_dto: RegisterDTO, db: Session = Depends(get_db)):
    """用户注册"""
    auth_service = AuthService(db)
    return auth_service.register(register_dto)

@router.post("/email/code", response_model=BaseResponse)
async def send_email_code(email_code_dto: EmailCodeDTO, db: Session = Depends(get_db)):
    """发送邮箱验证码"""
    auth_service = AuthService(db)
    return auth_service.send_email_code(email_code_dto.username)

@router.get("/info", response_model=BaseResponse)
async def get_user_info(current_user: SysUser = Depends(get_current_user)):
    """获取用户信息（需要认证）"""
    user_info = {
        "userId": current_user.user_id,
        "username": current_user.user_name,
        "nickName": current_user.nick_name,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "roles": [{"roleId": 1, "roleName": "管理员"}]
    }
    return BaseResponse(code=200, msg="获取成功", data=user_info)

@router.post("/logout", response_model=BaseResponse)
async def logout(current_user: SysUser = Depends(get_current_user)):
    """用户登出"""
    return BaseResponse(code=200, msg="登出成功", data=None)