from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.user import SysUser
from app.schemas.auth import LoginDTO, RegisterDTO, LoginVO, BaseResponse
from app.core.security import SecurityManager
from datetime import datetime

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return SecurityManager.verify_password(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return SecurityManager.get_password_hash(password)

    def authenticate_user(self, username: str, password: str):
        """认证用户"""
        user = self.db.query(SysUser).filter(
            or_(SysUser.user_name == username, SysUser.email == username)
        ).first()
        if not user:
            return None
        if not self.verify_password(password, user.password):
            return None
        return user

    def login(self, login_dto: LoginDTO) -> BaseResponse:
        """用户登录"""
        user = self.authenticate_user(login_dto.username, login_dto.password)
        if not user:
            return BaseResponse(code=500, msg="用户名或密码错误", data=None)
        
        # 创建JWT令牌
        access_token = SecurityManager.create_access_token(data={"sub": user.user_name})
        
        login_user = {
            "userId": user.user_id,
            "username": user.user_name,
            "nickName": user.nick_name,
            "email": user.email,
            "avatar": user.avatar,
            "roles": [{"roleId": 1, "roleName": "管理员"}]
        }
        
        login_vo = LoginVO(
            access_token=access_token,
            token=access_token,
            userInfo=login_user
        )
        
        # 更新最后登录时间
        user.login_date = datetime.now()
        self.db.commit()
        
        return BaseResponse(code=200, msg="登录成功", data=login_vo.dict())

    def register(self, register_dto: RegisterDTO) -> BaseResponse:
        """用户注册"""
        # 检查用户是否已存在
        existing_user = self.db.query(SysUser).filter(
            or_(SysUser.user_name == register_dto.username, SysUser.email == register_dto.username)
        ).first()
        
        if existing_user:
            return BaseResponse(code=500, msg="用户已存在", data=None)
        
        # 创建新用户
        new_user = SysUser(
            user_name=register_dto.username,
            email=register_dto.username,
            password=self.get_password_hash(register_dto.password),
            nick_name=register_dto.username.split('@')[0],
            status='0',
            del_flag='0',
            create_time=datetime.now(),
            update_time=datetime.now()
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        return BaseResponse(code=200, msg="注册成功", data=None)

    def send_email_code(self, email: str) -> BaseResponse:
        """发送邮箱验证码（模拟）"""
        return BaseResponse(code=200, msg="验证码发送成功", data=None)