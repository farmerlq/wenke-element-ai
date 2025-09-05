import type { ChatMessageVo, GetChatListParams, SendDTO } from './types';
import { get, post } from '@/utils/request';

/**
 * 发送消息
 */
export function send(data: SendDTO, type: 'stream' | 'json' = 'stream') {
  if (type === 'stream') {
    return post('/chat/send', data);
  } else {
    return post('/chat/send', data).json();
  }
};

// 获取聊天记录列表
export function getChatList(params: GetChatListParams) {
  return get<ChatMessageVo[]>('/system/message/list', params).json();
}

// 获取可用的AI智能体列表
export function getAgents() {
  return get('/chat/agents').json();
}
