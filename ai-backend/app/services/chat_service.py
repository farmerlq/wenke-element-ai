from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any, AsyncGenerator
import httpx
import json
import uuid
from datetime import datetime
from app.models.chat import ChatSession, ChatMessage
from app.models.user import SysUser
from app.models.agent import AiAgentConfig
from app.schemas.chat import SendDTO, GetChatListParams, ChatMessageResponse, ChatSessionResponse
from app.schemas.auth import BaseResponse
from app.adapters import AdapterFactory

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    async def send_message(self, send_dto: SendDTO, user_id: int) -> AsyncGenerator[str, None]:
        """发送消息到AI平台并返回流式响应"""
        
        # 获取用户选择的智能体配置
        try:
            agent_id = int(send_dto.agent_id)
        except (ValueError, TypeError):
            yield json.dumps({"error": "智能体ID格式无效"})
            return
            
        agent_config = self.db.query(AiAgentConfig).filter(
            and_(AiAgentConfig.agent_id == agent_id, AiAgentConfig.is_active == True)
        ).first()
        
        if not agent_config:
            yield json.dumps({"error": "智能体配置不存在"})
            return

        # 创建或获取会话
        if not send_dto.sessionId:
            session = ChatSession(
                title=f"新会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                user_id=user_id,
                agent_id=agent_config.agent_id
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            session_id = session.id
        else:
            session_id = send_dto.sessionId

        # 保存用户消息
        user_message = ChatMessage(
            session_id=session_id,
            message_type="user",
            content=send_dto.messages[-1].content if send_dto.messages else "",
            created_at=datetime.now()
        )
        self.db.add(user_message)
        self.db.commit()

        try:
            # 使用适配器工厂创建适配器
            adapter_config = {
                'base_url': agent_config.base_url,
                'api_key': agent_config.api_key,
                'agent_key': agent_config.agent_key,
                'bot_id': agent_config.bot_id,
                'access_token': agent_config.access_token,
                'enable_workflow_events': True,  # 启用Dify工作流事件透传，包括workflow_started事件
                'agent_id': agent_config.agent_id  # 添加agent_id参数，用于chat-messages格式
            }
            
            adapter = AdapterFactory.create_adapter(
                agent_config.platform_type, 
                adapter_config
            )
            
            
            
            # 获取用户消息
            user_message_content = send_dto.messages[-1].content if send_dto.messages else ""
            
            # 构建请求
            headers = adapter.build_request_headers()
            
            # 准备额外参数以支持chat-messages格式
            conversation_id = str(session_id) if session_id else ""
            
            payload = adapter.build_request_payload(
                user_message_content, 
                str(user_id), 
                send_dto.stream and agent_config.is_stream,  # 根据is_stream配置决定是否流式
                conversation_id=conversation_id
            )
            url = adapter.get_request_url()
            
            async with httpx.AsyncClient() as client:
                if send_dto.stream and agent_config.is_stream:
                    # 流式响应
                    async with client.stream(
                        "POST",
                        url,
                        headers=headers,
                        json=payload,
                        timeout=30.0
                    ) as response:
                        if response.status_code == 200:
                            # 收集完整内容并透传
                            full_content = ""
                            async for content_chunk in adapter.parse_stream_response(response):
                                if content_chunk:
                                    full_content += content_chunk
                                    yield content_chunk
                           
                            # 保存助手回复的完整内容
                            assistant_message = ChatMessage(
                                session_id=session_id,
                                message_type="assistant",
                                content=full_content,
                                created_at=datetime.now()
                            )
                            self.db.add(assistant_message)
                            self.db.commit()
                        else:
                            yield json.dumps({"error": f"AI平台调用失败: {response.status_code}"})
                else:
                    # 非流式响应
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=120.0
                    )
                    
                    try:
                        content = await adapter.parse_blocking_response(response)
                        
                        # 保存助手回复
                        assistant_message = ChatMessage(
                            session_id=session_id,
                            message_type="assistant",
                            content=content,
                            created_at=datetime.now()
                        )
                        self.db.add(assistant_message)
                        self.db.commit()
                        
                        yield json.dumps({"content": content})
                    except Exception as e:
                        yield json.dumps({"error": str(e)})
                        
        except Exception as e:
            yield json.dumps({"error": f"网络请求错误: {str(e)}"})

    def get_chat_list(self, params: GetChatListParams, user_id: int) -> BaseResponse:
        """获取聊天记录列表"""
        
        query = self.db.query(ChatMessage, ChatSession).join(
            ChatSession, ChatMessage.session_id == ChatSession.id
        ).filter(ChatSession.user_id == user_id)
        
        if params.sessionId:
            query = query.filter(ChatMessage.session_id == params.sessionId)
        
        if params.content:
            query = query.filter(ChatMessage.content.contains(params.content))
        
        if params.role:
            query = query.filter(ChatMessage.message_type == params.role)
        
        # 分页
        total = query.count()
        results = query.order_by(desc(ChatMessage.created_at)).offset(
            (params.pageNum - 1) * params.pageSize
        ).limit(params.pageSize).all()
        
        # 转换为响应格式
        message_list = []
        for msg, session in results:
            message_list.append(ChatMessageResponse(
                message_id=msg.id,
                session_id=msg.session_id,
                user_id=session.user_id,
                agent_id=session.agent_id,
                role=msg.message_type,
                content=msg.content,
                tokens=0 if msg.message_type == "user" else (msg.tokens_used or 0),  # 用户消息不包含token统计
                created_at=msg.created_at
            ).dict())
        
        return BaseResponse(
            code=200,
            msg="获取成功",
            data={"list": message_list, "total": total}
        )

    def get_sessions(self, user_id: int) -> BaseResponse:
        """获取用户会话列表"""
        
        sessions = self.db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(desc(ChatSession.updated_at)).all()
        
        session_list = []
        for session in sessions:
            session_list.append(ChatSessionResponse(
                session_id=session.id,
                session_name=session.title,
                user_id=session.user_id,
                agent_id=session.agent_id,
                created_at=session.created_at,
                updated_at=session.updated_at
            ).dict())
        
        return BaseResponse(code=200, msg="获取成功", data={"list": session_list, "total": len(session_list)})

    def delete_session(self, session_id: int, user_id: int) -> BaseResponse:
        """删除会话"""
        
        session = self.db.query(ChatSession).filter(
            and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
        ).first()
        
        if not session:
            return BaseResponse(code=500, msg="会话不存在", data=None)
        
        self.db.delete(session)
        self.db.commit()
        
        return BaseResponse(code=200, msg="删除成功", data=None)
