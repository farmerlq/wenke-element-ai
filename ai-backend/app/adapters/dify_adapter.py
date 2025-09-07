from typing import AsyncGenerator, Dict, Any, Optional
import json
import logging
from app.utils.dify_parser import DifyParser

logger = logging.getLogger(__name__)

class DifyAdapter:
    def __init__(self):
        self.parser = DifyParser()
        self.sent_events_set = set()

    async def parse_stream_response(self, response: AsyncGenerator[bytes, None]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        解析Dify流式响应，转换为标准化的事件格式
        """
        buffer = b""
        
        async for chunk in response:
            if chunk:
                buffer += chunk
                parsed_events = self.parser.parse_chunk(buffer)
                
                for event in parsed_events:
                    event_key = f"{event.get('event')}_{event.get('task_id', '')}"
                    
                    # 事件去重
                    if event_key in self.sent_events_set:
                        continue
                    
                    self.sent_events_set.add(event_key)
                    
                    # 标准化事件格式
                    standardized_event = self._standardize_event(event)
                    if standardized_event:
                        yield standardized_event
        
        # 发送DONE事件表示流结束
        yield {
            "event": "DONE",
            "data": {"message": "Stream completed"}
        }

    def _standardize_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """标准化Dify事件格式"""
        event_type = event.get("event")
        
        if event_type == "workflow_finished":
            return {
                "event": "workflow_finished",
                "data": event.get("data", {})
            }
        elif event_type == "node_started":
            return {
                "event": "node_started",
                "data": event.get("data", {})
            }
        elif event_type == "message":
            return {
                "event": "message",
                "data": {
                    "content": event.get("data", {}).get("text", ""),
                    "message_id": event.get("data", {}).get("id")
                }
            }
        
        return None