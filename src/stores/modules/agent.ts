import type { AgentVO } from '@/api/agent/types';
import { defineStore } from 'pinia';
import { getAgentList } from '@/api/agent';

// 智能体管理
export const useAgentStore = defineStore('agent', () => {
  // 当前智能体
  const currentAgentInfo = ref<AgentVO>({});

  // 设置当前智能体
  const setCurrentAgentInfo = (agentInfo: AgentVO) => {
    currentAgentInfo.value = agentInfo;
  };



  // 智能体菜单列表
  const agentList = ref<AgentVO[]>([]);
  // 请求智能体菜单列表
  const requestAgentList = async () => {
    try {
      const res = await getAgentList();
      agentList.value = res || [];
    }
    catch (error: any) {
      console.error('requestAgentList错误', error);
      // 如果是401错误，清空智能体列表
      if (error.status === 401 || error.response?.status === 401) {
        agentList.value = [];
      }
    }
  };

  return {
    currentAgentInfo,
    setCurrentAgentInfo,
    agentList,
    requestAgentList,
  };
});
