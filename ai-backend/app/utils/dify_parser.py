import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DifyParser:
    def __init__(self):
        self.buffer = b""
        self.max_buffer_size = 1024 * 1024  # 1MB

    def parse_chunk(self, chunk: bytes) -> List[Dict[str, Any]]:
        """
        解析数据块，提取完整的JSON事件
        """
        self.buffer += chunk
        
        # 防止缓冲区过大
        if len(self.buffer) > self.max_buffer_size:
            self.buffer = b""
        
        events = []
        lines = self.buffer.split(b'\n')
        
        # 保留最后不完整的行
        self.buffer = lines.pop() if lines else b""
        
        for line in lines:
            line = line.strip()
            if line:
                event = self._parse_line(line)
                if event:
                    events.append(event)
        
        return events

    def _parse_line(self, line: bytes) -> Optional[Dict[str, Any]]:
        """解析单行数据"""
        try:
            # 尝试解析为JSON
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                line_str = line_str[6:]  # 移除 'data: ' 前缀
            
            if line_str == '[DONE]':
                return {"event": "DONE"}
            
            data = json.loads(line_str)
            
            # 处理工作流事件
            if isinstance(data, dict):
                event_type = data.get("event")
                if event_type in ["workflow_finished", "node_started", "message"]:
                    return data
            
            # 处理消息内容
            if isinstance(data, dict) and "answer" in data:
                return {
                    "event": "message",
                    "data": {
                        "text": data["answer"],
                        "id": data.get("conversation_id")
                    }
                }
            
            return None
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return None

    def _parse_content(self, content: str) -> Dict[str, Any]:
        """解析内容字符串"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"text": content}