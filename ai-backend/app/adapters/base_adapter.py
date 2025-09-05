#!/usr/bin/env python3
"""
AI平台基础适配器接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator
import httpx

class BaseAIAdapter(ABC):
    """AI平台基础适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('base_url', '')
        self.api_key = config.get('api_key', '')
        self.agent_key = config.get('agent_key', '')
    
    @abstractmethod
    def build_request_headers(self) -> Dict[str, str]:
        """构建请求头"""
        pass
    
    @abstractmethod
    def build_request_payload(self, message: str, user_id: str, is_stream: bool = True) -> Dict[str, Any]:
        """构建请求载荷"""
        pass
    
    @abstractmethod
    async def parse_stream_response(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """解析流式响应"""
        pass
    
    @abstractmethod
    async def parse_blocking_response(self, response: httpx.Response) -> str:
        """解析非流式响应"""
        pass
    
    @abstractmethod
    def get_request_url(self) -> str:
        """获取请求URL"""
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否完整"""
        required_fields = ['base_url', 'api_key', 'agent_key']
        return all(self.config.get(field) for field in required_fields)