#!/usr/bin/env python3
"""
Dify平台适配器
"""

import json
import httpx
from typing import Dict, Any, AsyncGenerator
from .base_adapter import BaseAIAdapter

class DifyAdapter(BaseAIAdapter):
    """Dify平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 始终启用工作流事件透传，确保所有事件都能传递到前端
        self.enable_workflow_events = config.get('enable_workflow_events', True)
        # 从配置中提取并存储agent_id
        self.agent_id = config.get('agent_id')
    
    def build_request_headers(self) -> Dict[str, str]:
        """构建Dify请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def build_request_payload(self, message: str, user_id: str, is_stream: bool = False, **kwargs) -> dict:
        """构建请求载荷"""

        
        # 根据agent_key选择不同的请求格式
        if self.agent_key == 'workflows/run':
            # workflows/run 格式
            payload = {
                "inputs": {
                    "query": message
                },
                "response_mode": "streaming" if is_stream else "blocking",
                "user": user_id
            }
    
        elif self.agent_key == 'chat-messages':
            # chat-messages 格式
            conversation_id = kwargs.get('conversation_id', '')
            payload = self._build_chat_messages_payload(message, user_id, is_stream, conversation_id)
    
        else:
            # 默认格式
            payload = {
                "query": message,
                "stream": is_stream,
                "user": user_id
            }
    
        
        return payload
        
    def _build_chat_messages_payload(self, message: str, user_id: str, is_stream: bool, conversation_id: str) -> dict:
        """构建chat-messages格式的请求载荷"""

        
        # 确保message是字符串
        if not isinstance(message, str):
            message = str(message)
    
        
        # 使用与test_agent2_stream.py相同的格式 - 保持agent_id为整数类型
        payload = {
            "inputs": {},
            "query": message,
            "response_mode": "streaming" if is_stream else "blocking",
            "user": user_id,
            "agent_id": int(self.agent_id)  # 确保agent_id是整数类型
        }

        # 如果提供了conversation_id，添加到payload中
        
        return payload
    
    def get_request_url(self) -> str:
        """获取Dify请求URL"""
        return f"{self.base_url}/{self.agent_key}"
    
    async def parse_stream_response(self, response: httpx.Response) -> AsyncGenerator[str, None]:
        """解析Dify流式响应 - 确保输出格式符合前端要求且不包含任何额外字符"""
        if response.status_code != 200:
            # 确保错误响应是严格的JSON格式，不包含任何额外字符
            yield json.dumps({"content": f"Dify API调用失败: {response.status_code}", "error": True})
            return
        
        async for line in response.aiter_lines():
            line = line.strip()
            if not line or line == 'data: [DONE]':
                continue
            
            if line.startswith('data: '):
                data_content = line[6:].strip()
                
                try:
                    data = json.loads(data_content)
                    
                    # 专门处理Dify的text_chunk事件 - 主要适用于智能体=1
                    if data.get('event') == 'text_chunk':
                        # text_chunk事件处理
                        if 'text' in data:
                            text_content = str(data['text'])
                            # 确保输出是严格的JSON格式
                            yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                        elif 'data' in data and isinstance(data['data'], dict) and 'text' in data['data']:
                            # 处理可能嵌套在data中的text_chunk
                            text_content = str(data['data']['text'])
                            # 确保输出是严格的JSON格式
                            yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                    elif data.get('event') == 'message':
                        # message事件处理
                        # 首先检查并转发完整的message事件，确保前端能接收到所有工作事件
                        yield json.dumps({
                            "event": "message",
                            "data": data
                        })
                        
                        # 提取answer字段作为内容（某些接口的主要文本内容位置）
                        if 'answer' in data:
                            text_content = str(data['answer'])
                            # 确保输出是严格的JSON格式，同时包含内容和事件信息
                            yield json.dumps({
                                "content": text_content,
                                "event": "message",
                                "source": "answer",
                                "delta": {"content": text_content}  # 添加delta.content字段，兼容前端DifyRenderer
                            })
                        # 尝试从其他可能的字段中提取内容
                        elif 'text' in data:
                            text_content = str(data['text'])
                            yield json.dumps({
                                "content": text_content,
                                "event": "message",
                                "source": "text",
                                "delta": {"content": text_content}  # 添加delta.content字段，兼容前端DifyRenderer
                            })
                        elif 'data' in data and isinstance(data['data'], dict) and 'text' in data['data']:
                            text_content = str(data['data']['text'])
                            yield json.dumps({
                                "content": text_content,
                                "event": "message",
                                "source": "data.text"
                            })
                        elif 'outputs' in data and isinstance(data['outputs'], dict) and 'answer' in data['outputs']:
                            text_content = str(data['outputs']['answer'])
                            yield json.dumps({
                                "content": text_content,
                                "event": "message",
                                "source": "outputs.answer"
                            })
                    # 处理message_end事件
                    elif data.get('event') == 'message_end':
                        # 确保输出是严格的JSON格式
                        yield json.dumps({
                            "event": "message_end",
                            "data": data.get('data', {})
                        })
                    # 处理workflow_started事件，以正确的格式发送给前端
                    elif data.get('event') == 'workflow_started' and self.enable_workflow_events:
                        # 确保输出是严格的JSON格式
                        yield json.dumps({
                            "event": "workflow_started",
                            "data": data.get('data', {})
                        })
                    # 处理workflow_finished事件，从中提取文本内容
                    elif data.get('event') == 'workflow_finished' and 'data' in data:
                        workflow_data = data['data']
                        if isinstance(workflow_data, dict) and 'outputs' in workflow_data:
                            outputs = workflow_data['outputs']
                            if isinstance(outputs, dict):
                                # 支持多种可能的输出字段格式
                                if 'output' in outputs:
                                    text_content = str(outputs['output'])
                                    yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                                elif 'answer' in outputs:
                                    text_content = str(outputs['answer'])
                                    yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                                elif 'text' in outputs:
                                    text_content = str(outputs['text'])
                                    yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                        # 检查其他可能的文本字段路径
                        elif isinstance(workflow_data, dict) and 'output' in workflow_data:
                            text_content = str(workflow_data['output'])
                            yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                    # 通用处理逻辑：优先提取answer字段（某些接口可能会在其他事件中包含）
                        elif 'answer' in data:
                            # 对于任何包含answer字段的事件，都提取出来
                            text_content = str(data['answer'])
                            # 确保输出是严格的JSON格式
                            yield json.dumps({
                                "content": text_content,
                                "event": data.get('event', 'unknown'),
                                "source": "answer",
                                "delta": {"content": text_content}  # 添加delta.content字段，兼容前端DifyRenderer
                            })
                    # 检查是否有直接包含文本内容的其他事件类型
                        elif 'text' in data:
                            # 对于任何包含text字段的事件，都尝试提取文本内容
                            text_content = str(data['text'])
                            # 确保输出是严格的JSON格式
                            yield json.dumps({"content": text_content, "delta": {"content": text_content}})  # 添加delta.content字段，兼容前端DifyRenderer
                    else:
                        # 对于其他事件，以标准格式处理
                        if self.enable_workflow_events:
                            # 确保输出是严格的JSON格式，不含任何额外字符
                            event_data = {
                                "event": data.get('event', 'unknown'),
                                "data": data.get('data', {})
                            }
                            # 检查是否包含content字段，如果有，则提取出来
                            if 'content' in data:
                                event_data['content'] = str(data['content'])
                                event_data['delta'] = {"content": str(data['content'])}  # 添加delta.content字段，兼容前端DifyRenderer
                            # 检查是否包含answer字段（智能体2可能会在其他事件中包含）
                            elif 'answer' in data:
                                event_data['content'] = str(data['answer'])
                                event_data['delta'] = {"content": str(data['answer'])}  # 添加delta.content字段，兼容前端DifyRenderer
                            # 检查是否包含text字段（其他可能的内容字段）
                            elif 'text' in data:
                                event_data['content'] = str(data['text'])
                                event_data['delta'] = {"content": str(data['text'])}  # 添加delta.content字段，兼容前端DifyRenderer
                            yield json.dumps(event_data)
                            
                except json.JSONDecodeError:
                    # 如果不是JSON，以标准格式发送内容
                    if data_content.strip():
                        # 确保输出是严格的JSON格式，不含任何额外字符
                        yield json.dumps({"content": data_content, "delta": {"content": data_content}})  # 添加delta.content字段，兼容前端DifyRenderer
    
    async def parse_blocking_response(self, response: httpx.Response) -> str:
        """解析Dify非流式响应"""
        if response.status_code != 200:
            raise Exception(f"Dify API调用失败: {response.status_code}")
        
        response_data = response.json()
        
        if 'data' in response_data and 'outputs' in response_data['data']:
            outputs = response_data['data']['outputs']
            if isinstance(outputs, dict) and 'output' in outputs:
                return outputs['output']
            else:
                return str(outputs)
        
        raise Exception("无法解析Dify响应格式")
