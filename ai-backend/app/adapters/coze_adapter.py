#!/usr/bin/env python3
"""
Coze平台适配器
"""

import json
import httpx
from typing import Dict, Any, AsyncGenerator
from .base_adapter import BaseAIAdapter

class CozeAdapter(BaseAIAdapter):
    """Coze平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_id = config.get('bot_id', '')
        self.access_token = config.get('access_token', '')
    
    def build_request_headers(self) -> Dict[str, str]:
        """构建Coze请求头"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def build_request_payload(self, message: str, user_id: str, is_stream: bool = True) -> Dict[str, Any]:
        """构建Coze请求载荷"""
        payload = {
            "bot_id": self.bot_id,
            "user_id": str(user_id),
            "query": message,
            "stream": is_stream
        }
        return payload
    
    def get_request_url(self) -> str:
        """获取Coze请求URL"""
        return f"{self.base_url}/chat"
    
    async def parse_stream_response(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """解析Coze流式响应"""
        if response.status_code != 200:
            yield json.dumps({"error": f"Coze API调用失败: {response.status_code}"})
            return
        
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # Coze流式响应格式
                if 'choices' in data and data['choices']:
                    choice = data['choices'][0]
                    if 'delta' in choice and 'content' in choice['delta']:
                        content = choice['delta']['content']
                        if content:
                            yield content
                            
            except json.JSONDecodeError:
                continue
    
    async def parse_blocking_response(self, response: httpx.Response) -> str:
        """解析Coze非流式响应"""
        if response.status_code != 200:
            raise Exception(f"Coze API调用失败: {response.status_code}")
        
        response_data = response.json()
        
        if 'choices' in response_data and response_data['choices']:
            choice = response_data['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                return choice['message']['content']
        
        raise Exception("无法解析Coze响应格式")
    
    def validate_config(self) -> bool:
        """验证Coze配置是否完整"""
        required_fields = ['base_url', 'access_token', 'bot_id']
        return all(self.config.get(field) for field in required_fields)