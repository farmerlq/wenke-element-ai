import type { AgentVO } from './types';
import { get } from '@/utils/request';

// 获取当前用户的智能体列表（使用agents接口）
export function getAgentList() {
  return get<{
    data: AgentVO[];
  }>('/chat/agents').json().then(res => res.data);
}
