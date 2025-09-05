#!/usr/bin/env python3
"""
n8n平台适配器
"""

import json
import httpx
from typing import Dict, Any, AsyncGenerator
from .base_adapter import BaseAIAdapter

class N8NAdapter(BaseAIAdapter):
    """n8n平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
    
    def build_request_headers(self) -> Dict[str, str]:
        """构建n8n请求头"""
        return {
            "Content-Type": "application/json"
        }
    
    def build_request_payload(self, message: str, user_id: str, is_stream: bool = True) -> Dict[str, Any]:
        """构建n8n请求载荷"""
        return {
            "message": message,
            "user_id": str(user_id),
            "stream": is_stream
        }
    
    def get_request_url(self) -> str:
        """获取n8n请求URL"""
        return self.agent_key  # n8n使用webhook URL作为agent_key
    
    async def parse_stream_response(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """解析n8n流式响应"""
        if response.status_code != 200:
            yield json.dumps({"error": f"n8n API调用失败: {response.status_code}"})
            return
        
        # n8n webhook通常返回完整响应
        # 这里模拟流式传输，按字符分割
        content = await response.aread()
        text = content.decode('utf-8')
        
        # 按字符流式传输
        for char in text:
            yield char
    
    async def parse_blocking_response(self, response: httpx.Response) -> str:
        """解析n8n非流式响应"""
        if response.status_code != 200:
            raise Exception(f"n8n API调用失败: {response.status_code}")
        
        content = await response.aread()
        return content.decode('utf-8')
    
    def validate_config(self) -> bool:
        """验证n8n配置是否完整"""
        required_fields = ['agent_key']  # n8n只需要webhook URL
        return all(self.config.get(field) for field in required_fields)