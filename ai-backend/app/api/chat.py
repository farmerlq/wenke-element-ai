from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from app.db.database import get_db
from app.services.chat_service import ChatService
from app.schemas.chat import SendDTO, GetChatListParams
from app.schemas.auth import BaseResponse
from app.core.dependencies import get_current_user
from app.models.user import SysUser
from typing import Optional
import json

router = APIRouter(prefix="/chat", tags=["聊天管理"])

@router.post("/send")
async def send_message(
    send_dto: SendDTO, 
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """发送消息到AI平台（需要认证）"""
    chat_service = ChatService(db)
    
    # 如果stream=false，返回普通JSON响应
    if not send_dto.stream:
        content = ""
        async for chunk in chat_service.send_message(send_dto, current_user.user_id):
            try:
                data = json.loads(chunk)
                content = data.get("content", "")
            except:
                content = chunk
        return {"code": 200, "msg": "成功", "data": {"content": content}}
    
    # 如果stream=true，返回SSE流
    async def generate():
        async for chunk in chat_service.send_message(send_dto, current_user.user_id):
            yield f"data: {chunk}\n\n"
    
    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # 禁用Nginx缓冲
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS'
        }
    )

@router.get("/list")
async def get_chat_list(
    sessionId: Optional[str] = None,
    content: Optional[str] = None,
    role: Optional[str] = None,
    pageNum: int = 1,
    pageSize: int = 10,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取聊天记录列表（需要认证）"""
    chat_service = ChatService(db)
    params = GetChatListParams(
        sessionId=sessionId,
        content=content,
        role=role,
        pageNum=pageNum,
        pageSize=pageSize
    )
    return chat_service.get_chat_list(params, current_user.user_id)

@router.get("/sessions")
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取用户会话列表（需要认证）"""
    chat_service = ChatService(db)
    return chat_service.get_sessions(current_user.user_id)

@router.delete("/session/{session_id}")
async def delete_session(
    session_id: int, 
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """删除会话（需要认证）"""
    chat_service = ChatService(db)
    return chat_service.delete_session(session_id, current_user.user_id)

@router.get("/agents")
async def get_agents(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user)
):
    """获取可用的AI智能体列表（需要认证）"""
    from app.models.agent import AiAgentConfig
    agents = db.query(AiAgentConfig).filter(AiAgentConfig.is_active == True).all()
    
    return {
        "code": 200,
        "msg": "获取成功",
        "data": [
            {
                "agentId": agent.agent_id,
                "agentName": agent.agent_name,
                "platformType": agent.platform_type,
                "description": agent.description,
                "isDefault": agent.is_default
            }
            for agent in agents
        ]
    }
