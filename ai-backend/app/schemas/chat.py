from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ToolCallFunction(BaseModel):
    arguments: Optional[str] = None
    name: Optional[str] = None

class ToolCalls(BaseModel):
    function: Optional[ToolCallFunction] = None
    id: Optional[str] = None
    type: Optional[str] = None

class Message(BaseModel):
    content: Optional[str] = None
    name: Optional[str] = None
    reasoning_content: Optional[str] = None
    role: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[ToolCalls]] = None

class SendDTO(BaseModel):
    appId: Optional[str] = None
    contentNumber: Optional[int] = None
    isMcp: Optional[bool] = None
    agent_id: str  # 必需参数
    messages: List[Message]
    prompt: Optional[str] = None
    search: Optional[bool] = None
    sessionId: Optional[int] = None
    stream: Optional[bool] = True
    sysPrompt: Optional[str] = None
    userId: Optional[int] = None
    usingContext: Optional[bool] = None

class GetChatListParams(BaseModel):
    content: Optional[str] = None
    createBy: Optional[int] = None
    createDept: Optional[int] = None
    createTime: Optional[datetime] = None
    deductCost: Optional[float] = None
    id: Optional[int] = None
    isAsc: Optional[str] = None
    orderByColumn: Optional[str] = None
    pageNum: Optional[int] = 1
    pageSize: Optional[int] = 10
    params: Optional[Dict[str, Any]] = None
    remark: Optional[str] = None
    role: Optional[str] = None
    sessionId: Optional[int] = None
    totalTokens: Optional[int] = None
    updateBy: Optional[int] = None
    updateTime: Optional[datetime] = None
    userId: Optional[int] = None

class ChatMessageVo(BaseModel):
    content: Optional[str] = None
    deductCost: Optional[float] = None
    id: Optional[int] = None

class ChatSessionResponse(BaseModel):
    session_id: int
    session_name: Optional[str] = None
    user_id: int
    agent_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ChatMessageResponse(BaseModel):
    message_id: int
    session_id: int
    user_id: int
    agent_id: int
    role: str
    content: Optional[str] = None
    content_type: str = "text"
    tokens: int = 0
    created_at: datetime