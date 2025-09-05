from pydantic import BaseModel, EmailStr
from typing import Optional, List

class LoginDTO(BaseModel):
    username: str
    password: str
    code: Optional[str] = None
    confirmPassword: Optional[str] = None

class RegisterDTO(BaseModel):
    username: EmailStr
    password: str
    code: str
    confirmPassword: Optional[str] = None

class EmailCodeDTO(BaseModel):
    username: EmailStr

class RoleDTO(BaseModel):
    dataScope: Optional[str] = None
    roleId: Optional[int] = None
    roleKey: Optional[str] = None
    roleName: Optional[str] = None

class LoginUser(BaseModel):
    avatar: Optional[str] = None
    browser: Optional[str] = None
    deptId: Optional[int] = None
    deptName: Optional[str] = None
    expireTime: Optional[int] = None
    ipaddr: Optional[str] = None
    loginId: Optional[str] = None
    loginLocation: Optional[str] = None
    loginTime: Optional[int] = None
    menuPermission: Optional[List[str]] = None
    nickName: Optional[str] = None
    os: Optional[str] = None
    roleId: Optional[int] = None
    rolePermission: Optional[List[str]] = None
    roles: Optional[List[RoleDTO]] = None
    tenantId: Optional[str] = None
    token: Optional[str] = None
    userId: Optional[int] = None
    username: Optional[str] = None
    userType: Optional[str] = None

class LoginVO(BaseModel):
    access_token: Optional[str] = None
    token: Optional[str] = None
    userInfo: Optional[LoginUser] = None

class BaseResponse(BaseModel):
    code: int
    data: Optional[dict] = None
    msg: str
    rows: Optional[List[dict]] = None