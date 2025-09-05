from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.chat_service import ChatService
from app.schemas.auth import BaseResponse
from app.core.dependencies import get_current_user
from app.models.user import SysUser
from app.models.chat import ChatSession

router = APIRouter(prefix="/system", tags=["系统管理"])

@router.get("/session/list")
async def get_session_list(
    pageNum: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取用户会话列表（需要认证）"""
    chat_service = ChatService(db)
    result = chat_service.get_sessions(current_user.user_id)
    
    # 模拟分页处理（因为原get_sessions返回所有数据）
    if result.data and result.data["list"]:
        total = len(result.data["list"])
        start = (pageNum - 1) * pageSize
        end = start + pageSize
        paginated_list = result.data["list"][start:end]
        
        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "list": paginated_list,
                "total": total
            }
        }
    
    return result

from pydantic import BaseModel

class CreateSessionDTO(BaseModel):
    sessionTitle: str
    userId: int
    
@router.post("/session")
async def create_session(
    session_data: CreateSessionDTO,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """创建新会话（需要认证）"""
    try:
        # 默认使用ID为1的智能体
        default_agent_id = 1
        
        # 创建新会话
        new_session = ChatSession(
            title=session_data.sessionTitle if session_data.sessionTitle else f"新会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            user_id=current_user.user_id,
            agent_id=default_agent_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        return {
            "code": 200,
            "msg": "创建成功",
            "data": {
                "sessionId": new_session.id,
                "sessionTitle": new_session.title,
                "userId": new_session.user_id,
                "agentId": new_session.agent_id,
                "createdAt": new_session.created_at,
                "updatedAt": new_session.updated_at
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"创建失败: {str(e)}",
            "data": None
        }

class UpdateSessionDTO(BaseModel):
    id: str
    sessionTitle: str
    # 以下字段为前端可能传递的可选字段
    remark: Optional[str] = None
    sessionContent: Optional[str] = None
    session_name: Optional[str] = None
    userId: Optional[int] = None
    user_id: Optional[int] = None
    createTime: Optional[datetime] = None
    created_at: Optional[datetime] = None
    prefixIcon: Optional[Any] = None
    
@router.put("/session")
async def update_session(
    session_data: UpdateSessionDTO,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """更新会话信息（需要认证）"""
    try:
        # 查找会话
        session = db.query(ChatSession).filter(
            ChatSession.id == int(session_data.id),
            ChatSession.user_id == current_user.user_id
        ).first()
        
        if not session:
            return {
                "code": 500,
                "msg": "会话不存在",
                "data": None
            }
        
        # 更新会话信息
        session.title = session_data.sessionTitle
        session.updated_at = datetime.now()
        
        db.commit()
        
        return {
            "code": 200,
            "msg": "更新成功",
            "data": {
                "sessionId": session.id,
                "sessionTitle": session.title
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"更新失败: {str(e)}",
            "data": None
        }

@router.get("/session/{id}")
async def get_session(
    id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取单个会话详情（需要认证）"""
    try:
        # 查找会话
        session = db.query(ChatSession).filter(
            ChatSession.id == id,
            ChatSession.user_id == current_user.user_id
        ).first()
        
        if not session:
            return {
                "code": 500,
                "msg": "会话不存在",
                "data": None
            }
        
        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "id": str(session.id),
                "sessionTitle": session.title,
                "userId": session.user_id,
                "agentId": session.agent_id,
                "createdAt": session.created_at,
                "updatedAt": session.updated_at
            }
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"获取失败: {str(e)}",
            "data": None
        }

@router.delete("/session/{ids}")
async def delete_session(
    ids: str,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """批量删除会话（需要认证）"""
    try:
        # 处理多个ID
        id_list = ids.split(',')
        
        for session_id in id_list:
            try:
                int_id = int(session_id)
                chat_service = ChatService(db)
                result = chat_service.delete_session(int_id, current_user.user_id)
                
                if result.code != 200:
                    return result
            except ValueError:
                continue
        
        return {
            "code": 200,
            "msg": "删除成功",
            "data": None
        }
    except Exception as e:
        return {
            "code": 500,
            "msg": f"删除失败: {str(e)}",
            "data": None
        }

@router.get("/message/list")
async def get_message_list(
    sessionId: int = None,
    pageNum: int = 1,
    pageSize: int = 10,
    content: str = None,
    role: str = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取聊天记录列表（需要认证）"""
    try:
        chat_service = ChatService(db)
        
        # 创建查询参数对象
        class GetChatListParams:
            def __init__(self, sessionId, pageNum, pageSize, content, role):
                self.sessionId = sessionId
                self.pageNum = pageNum
                self.pageSize = pageSize
                self.content = content
                self.role = role
        
        params = GetChatListParams(sessionId, pageNum, pageSize, content, role)
        result = chat_service.get_chat_list(params, current_user.user_id)
        
        return result
    except Exception as e:
        return {
            "code": 500,
            "msg": f"获取失败: {str(e)}",
            "data": None
        }