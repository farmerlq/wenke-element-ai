#!/usr/bin/env python3
"""
Dify平台适配器
"""

import json
import httpx
import logging
from typing import Dict, Any, AsyncGenerator
from .base_adapter import BaseAIAdapter

logger = logging.getLogger(__name__)

class DifyAdapter(BaseAIAdapter):
    """Dify平台适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 始终启用工作流事件透传，确保所有事件都能传递到前端
        self.enable_workflow_events = config.get('enable_workflow_events', True)
        # 从配置中提取并存储agent_id
        self.agent_id = config.get('agent_id')

    def clean_json_string(self, json_str: str) -> str:
        """清理和修复JSON字符串，处理常见的格式问题"""
        cleaned = json_str.strip()
        
        # 处理不完整的Unicode转义序列
        if '\\u' in cleaned:
            # 修复content字段的Unicode转义序列问题
            import re
            # 修复不完整的content字段 - 处理类似 "content": \\u56de\\u7b54 的情况
            cleaned = re.sub(r'"content"\s*:\s*([^,\}\]\]]+)(,|\}|\])', 
                            lambda m: f'"content": "{m.group(1)}"{m.group(2)}' 
                            if m.group(1) and '\\u' in m.group(1) and not m.group(1).startswith('"') 
                            else m.group(0), cleaned)
            
            # 处理完全没有引号且包含Unicode转义序列的content字段
            cleaned = re.sub(r'"content"\s*:\s*([^,\}\]\]]*\\u[0-9a-fA-F]{4}[^,\}\]\]]*)(,|\}|\])',
                            lambda m: f'"content": "{m.group(1)}"{m.group(2)}'
                            if m.group(1) and not m.group(1).startswith('"') 
                            else m.group(0), cleaned)
            
            # 处理以Unicode转义序列开头但没有引号的情况
            cleaned = re.sub(r'"content"\s*:\s*(\\u[0-9a-fA-F]{4}[^,\}\]\]]*)(,|\}|\])',
                            lambda m: f'"content": "{m.group(1)}"{m.group(2)}'
                            if m.group(1) and not m.group(1).startswith('"')
                            else m.group(0), cleaned)
        
        # 处理node_started事件的title字段问题
        if '"node_started"' in cleaned and '"title":' in cleaned:
            import re
            # 修复title字段没有引号的问题
            cleaned = re.sub(r'"title"\s*:\s*([^,\}\]\]]+)(,|\}|\])',
                            lambda m: f'"title": "{m.group(1)}"{m.group(2)}'
                            if m.group(1) and not m.group(1).startswith('"') and not m.group(1).endswith('"')
                            else m.group(0), cleaned)
        
        # 处理message_id和node_id字段的UUID截断问题
        if ('"message_id":' in cleaned or '"node_id":' in cleaned) and '"event":' in cleaned and not cleaned.endswith('}'):
            import re
            # 检查是否缺少闭合括号
            open_braces = cleaned.count('{')
            close_braces = cleaned.count('}')
            if open_braces > close_braces:
                cleaned += '}' * (open_braces - close_braces)
            
            # 处理UUID截断模式
            uuid_pattern = r'"(message_id|node_id)"\s*:\s*"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{1,12})"[^"]*'
            uuid_match = re.search(uuid_pattern, cleaned)
            if uuid_match and uuid_match.group(2):
                truncated_uuid = uuid_match.group(2)
                # 如果UUID被截断（少于36个字符），使用随机字符补全
                if len(truncated_uuid) < 36:
                    full_uuid = truncated_uuid.ljust(36, '0')[:36]
                    cleaned = cleaned.replace(f'"{uuid_match.group(1)}": "{truncated_uuid}"', f'"{uuid_match.group(1)}": "{full_uuid}"')
        
        # 检查是否以不完整的对象结尾
        if cleaned.startswith('{') and not cleaned.endswith('}'):
            # 如果包含常见字段，尝试补全括号
            if any(field in cleaned for field in ['"event"', '"message_id"', '"data"', '"content"', '"text"', '"answer"']):
                cleaned += '}'
        
        # 检查是否以不完整的数组结尾
        if cleaned.startswith('[') and not cleaned.endswith(']'):
            cleaned += ']'
            
        # 处理多个JSON对象拼接的情况
        if cleaned.count('{') > cleaned.count('}'):
            # 如果开括号比闭括号多，补全缺失的闭括号
            cleaned += '}' * (cleaned.count('{') - cleaned.count('}'))
        elif cleaned.count('[') > cleaned.count(']'):
            # 如果开方括号比闭方括号多，补全缺失的闭方括号
            cleaned += ']' * (cleaned.count('[') - cleaned.count(']'))
            
        return cleaned
    
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
        """解析Dify流式响应 - 完全处理数据块解析，不再依赖前端DifyRenderer"""
        if response.status_code != 200:
            # 确保错误响应是严格的JSON格式，不包含任何额外字符
            yield json.dumps({"content": f"Dify API调用失败: {response.status_code}", "error": True})
            return
        
        # 用于跟踪已发送的内容，避免重复
        sent_content_set = set()
        
        async for line in response.aiter_lines():
            line = line.strip()
            if not line or line == 'data: [DONE]':
                continue
            
            if line.startswith('data: '):
                data_content = line[6:].strip()
                
                # 调试日志：记录原始数据
                logger.debug(f"Raw Dify response: {data_content}")
                
                # 先尝试清理JSON字符串
                cleaned_data = self.clean_json_string(data_content)
                
                try:
                    data = json.loads(cleaned_data)
                    
                    # 调试日志：记录解析后的数据
                    logger.debug(f"Parsed JSON data: {data}")
                    
                    # 提取实际内容（实现前端DifyParser.extractContent的所有逻辑）
                    extracted_content = self._extract_content(data)
                    
                    # 调试日志：记录提取的内容
                    logger.debug(f"Extracted content: '{extracted_content}', Event: {data.get('event')}")
                    
                    if extracted_content:
                        # 去重逻辑：检查内容是否已经发送过
                        if extracted_content in sent_content_set:
                            logger.debug(f"跳过重复内容: '{extracted_content}'")
                            continue
                        
                        # 记录已发送的内容
                        sent_content_set.add(extracted_content)
                        
                        # 对于有效内容，返回标准格式，同时保留原始事件信息
                        yield json.dumps({
                            "content": extracted_content,
                            "delta": {"content": extracted_content},
                            "event": data.get('event'),
                            "data": data.get('data', {})
                        })
                    elif self.enable_workflow_events:
                        # 对于工作流事件，返回事件信息，同时包含content字段用于前端显示
                        event_data = {
                            "content": "",  # 确保content字段存在
                            "event": data.get('event'),
                            "data": data.get('data', {})
                        }
                        yield json.dumps(event_data)
                    
                except json.JSONDecodeError:
                    # 调试日志：记录JSON解析错误
                    logger.warning(f"JSON decode error for: {data_content}")
                    
                    # 如果不是JSON，尝试直接提取内容
                    if data_content.strip():
                        # 检查是否为有效内容
                        if self._is_valid_content(data_content):
                            # 去重逻辑：检查内容是否已经发送过
                            if data_content in sent_content_set:
                                logger.debug(f"跳过重复内容: '{data_content}'")
                                continue
                            
                            # 记录已发送的内容
                            sent_content_set.add(data_content)
                            
                            yield json.dumps({
                                "content": data_content,
                                "delta": {"content": data_content}
                            })
    
    def _extract_content(self, data: dict) -> str:
        """提取实际内容 - 实现前端DifyParser.extractContent的所有逻辑"""
        if not data or not isinstance(data, dict):
            return ""
        
        # 1. 处理message事件中的顶层answer字段
        if data.get('event') == 'message' and data.get('answer') and isinstance(data['answer'], str) and data['answer'].strip():
            return data['answer'].strip()
        
        # 2. 处理text_chunk事件中的data.text字段
        if data.get('event') == 'text_chunk' and data.get('data') and isinstance(data['data'], dict):
            text = data['data'].get('text')
            if text and isinstance(text, str) and text.strip() and self._is_valid_content(text):
                return text.strip()
        
        # 3. 处理Dify标准格式的answer字段
        if data.get('answer') and isinstance(data['answer'], str) and data['answer'].strip():
            return data['answer'].strip()
        
        # 4. 处理delta.content字段 (支持与OpenAI兼容的格式)
        if data.get('delta') and isinstance(data['delta'], dict):
            content = data['delta'].get('content')
            if content and isinstance(content, str) and content.strip() and self._is_valid_content(content):
                return content.strip()
        
        # 5. 处理outputs.answer字段
        if data.get('outputs') and isinstance(data['outputs'], dict):
            answer = data['outputs'].get('answer')
            if answer and isinstance(answer, str) and answer.strip() and self._is_valid_content(answer):
                return answer.strip()
        
        # 6. 处理text字段
        if data.get('text') and isinstance(data['text'], str) and data['text'].strip() and self._is_valid_content(data['text']):
            return data['text'].strip()
        
        # 7. 处理content字段
        if data.get('content') and isinstance(data['content'], str) and data['content'].strip() and self._is_valid_content(data['content']):
            return data['content'].strip()
        
        # 8. 处理嵌套数据中的text字段
        if data.get('data') and isinstance(data['data'], dict):
            text = data['data'].get('text')
            if text and isinstance(text, str) and text.strip() and self._is_valid_content(text):
                return text.strip()
        
        # 9. 处理嵌套数据中的content字段
        if data.get('data') and isinstance(data['data'], dict):
            content = data['data'].get('content')
            if content and isinstance(content, str) and content.strip() and self._is_valid_content(content):
                return content.strip()
        
        # 10. 处理OpenAI格式的流式响应
        if data.get('choices') and isinstance(data['choices'], list) and len(data['choices']) > 0:
            choice = data['choices'][0]
            if choice and isinstance(choice, dict) and choice.get('delta') and isinstance(choice['delta'], dict):
                content = choice['delta'].get('content')
                if content and isinstance(content, str) and content.strip() and self._is_valid_content(content):
                    return content.strip()
        
        # 11. 处理可能的其他格式
        if data.get('result') and isinstance(data['result'], str) and data['result'].strip() and self._is_valid_content(data['result']):
            return data['result'].strip()
        
        # 12. 处理tts_message中的audio字段
        if data.get('event') == 'tts_message' and data.get('audio') and isinstance(data['audio'], str) and data['audio'].strip():
            return data['audio'].strip()
        
        # 13. 处理workflow_finished事件中的输出
        if data.get('event') == 'workflow_finished' and data.get('data') and isinstance(data['data'], dict):
            workflow_data = data['data']
            # 检查outputs字段
            if workflow_data.get('outputs') and isinstance(workflow_data['outputs'], dict):
                outputs = workflow_data['outputs']
                if outputs.get('output') and isinstance(outputs['output'], str) and outputs['output'].strip():
                    return outputs['output'].strip()
                elif outputs.get('answer') and isinstance(outputs['answer'], str) and outputs['answer'].strip():
                    return outputs['answer'].strip()
                elif outputs.get('text') and isinstance(outputs['text'], str) and outputs['text'].strip():
                    return outputs['text'].strip()
            # 检查直接output字段
            elif workflow_data.get('output') and isinstance(workflow_data['output'], str) and workflow_data['output'].strip():
                return workflow_data['output'].strip()
        
        return ""
    
    def _is_valid_content(self, content: str) -> bool:
        """判断内容是否为有效内容（非元数据）"""
        if not content or not content.strip():
            return False
        
        # 排除特殊的控制信息标记，但允许[DONE]作为有效事件数据
        control_markers = ['[DONE]', '[DONE', 'DONE]', 'DONE']
        for marker in control_markers:
            if content == marker:
                return True
            if marker in content and content != marker:
                return False
        
        return True
    
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
