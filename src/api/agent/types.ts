// 查询用户智能体列表返回的数据结构
export interface AgentVO {
  agentId?: number;
  agentName?: string;
  platformType?: string;
  description?: string;
  isDefault?: boolean;
  // 兼容性字段
  id?: number;
  modelName?: string;
  category?: string;
  modelDescribe?: string; // 保持兼容性，实际为agentDescribe
  modelPrice?: number; // 保持兼容性，实际为agentPrice
  modelType?: string; // 保持兼容性，实际为agentType
  modelShow?: string; // 保持兼容性，实际为agentShow
  systemPrompt?: string;
  apiHost?: string;
  apiKey?: string;
  remark?: string;
}
