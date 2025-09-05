<!-- 每个回话对应的聊天内容 -->
<script setup lang="ts">
import type { AnyObject } from 'typescript-api-pro';
import type { BubbleProps } from 'vue-element-plus-x/types/Bubble';
import type { BubbleListInstance } from 'vue-element-plus-x/types/BubbleList';
import type { FilesCardProps } from 'vue-element-plus-x/types/FilesCard';
import type { ThinkingStatus } from 'vue-element-plus-x/types/Thinking';
import type { SendDTO } from '@/api/chat/types';
import { useHookFetch } from 'hook-fetch/vue';
import { Sender, BubbleList, Thinking, XMarkdown } from 'vue-element-plus-x';
import { useRoute } from 'vue-router';
import { send } from '@/api';
import FilesSelect from '@/components/FilesSelect/index.vue';
import ModelSelect from '@/components/ModelSelect/index.vue';
import { useChatStore } from '@/stores/modules/chat';
import { useFilesStore } from '@/stores/modules/files';
import { useAgentStore } from '@/stores/modules/agent';
import { useUserStore } from '@/stores/modules/user';
import { ElMessage } from 'element-plus';
import { ArrowLeftBold, ArrowRightBold } from '@element-plus/icons-vue';
import { computed, ref, watch, nextTick } from 'vue';
import { DifyRenderer } from '@/utils/dify-parser.ts';

// 定义工作流事件项类型
interface WorkflowEventItem {
  type: string;
  message: string;
  data: AnyObject;

  dataCollapsed?: boolean;
}

type MessageItem = BubbleProps & {
  key: number;
  role: 'ai' | 'user' | 'system';
  avatar: string;
  thinkingStatus?: ThinkingStatus;
  thinlCollapse?: boolean;
  reasoning_content?: string;
  typing?: boolean;
  workflowEvents?: WorkflowEventItem[];
  workflowEventsCollapsed?: boolean;
  totalTokens?: number; // 总token数
  totalCost?: number;   // 总花费
  timestamp?: string;   // 消息时间戳
};

const route = useRoute();
const chatStore = useChatStore();
const agentStore = useAgentStore();
const filesStore = useFilesStore();
const userStore = useUserStore();

// 用户头像
const avatar = computed(() => {
  const userInfo = userStore.userInfo;
  return userInfo?.avatar || new URL('@/assets/images/logo.png', import.meta.url).href;
});

const inputValue = ref('');
const senderRef = ref<InstanceType<typeof Sender> | null>(null);
const bubbleItems = ref<MessageItem[]>([]);
const bubbleListRef = ref<BubbleListInstance | null>(null);

// Dify响应渲染器
const difyRenderer = new DifyRenderer();

const { loading: isLoading, cancel } = useHookFetch({
  request: send,
  onError: (err) => {
    console.warn('测试错误拦截', err);
  },
});
// 记录进入思考中
const isThinking = ref(false);

watch(
  () => route.params?.id,
  async (_id_) => {
    if (_id_) {
      // 确保_id_是一个有效的字符串
      const sessionId = typeof _id_ === 'object' ? String(_id_) : _id_;
      
      if (sessionId !== 'not_login') {
        // 判断的当前会话id是否有聊天记录，有缓存则直接赋值展示
        const chatData = chatStore.chatMap[sessionId];
        if (chatData && Array.isArray(chatData) && chatData.length > 0) {
          bubbleItems.value = chatData as MessageItem[];
          // 滚动到底部
          setTimeout(() => {
            bubbleListRef.value?.scrollToBottom();
          }, 350);
          return;
        }

        // 无缓存则请求聊天记录
        await chatStore.requestChatList(sessionId);
        // 请求聊天记录后，赋值回显，并滚动到底部
        const newChatData = chatStore.chatMap[sessionId];
        bubbleItems.value = (newChatData && Array.isArray(newChatData)) ? newChatData as MessageItem[] : [];

        // 滚动到底部
        setTimeout(() => {
          bubbleListRef.value?.scrollToBottom();
        }, 350);
      }

      // 如果本地有发送内容 ，则直接发送
      const v = localStorage.getItem('chatContent');
      if (v) {
        // 发送消息
    
        setTimeout(() => {
          startSSE(v);
        }, 350);

        localStorage.removeItem('chatContent');
      }
    }
  },
  { immediate: true, deep: true },
);

// 定义工作流事件类型
interface WorkflowEvent {
  event: 'workflow_started' | 'node_started' | 'node_finished' | 'workflow_finished';
  data?: {
    workflow_run_id?: string;
    node_id?: string;
    node_name?: string;
    node_type?: string;
    [key: string]: any;
  };
  message?: string;
  dataCollapsed?: boolean;
}

// 处理数据块 - 利用增强的DifyRenderer处理SSE数据
function handleDataChunk(chunk: any) {
  
  if (!chunk) return;

  try {
    const lastItem = bubbleItems.value[bubbleItems.value.length - 1];
    if (!lastItem) return;

    // 使用增强的DifyRenderer处理数据块，支持多种格式
    difyRenderer.handleChunk(
      chunk,
      (content: string, metadata?: AnyObject) => {
        if (content && content.trim().length > 0) {
          // 直接使用流式内容，不使用打字机效果
          appendContent(content);
        }
        else if (metadata && ['workflow_started', 'node_started', 'node_finished', 'workflow_finished', 'message_end'].includes(metadata.event)) {
          // 处理工作流事件
          const workflowEvent = metadata as WorkflowEvent;

          // 格式化事件消息
          const eventMessages: Record<string, string> = {
            'workflow_started': '开始理解你的语义',
            'node_started': '正在调用LLM（大模型）',
            'node_finished': '调用完毕',
            'workflow_finished': '任务完成',
            'message_end': '消息已完成'
          };

          let message = eventMessages[workflowEvent.event] || workflowEvent.event;

          // 如果事件有自定义文本，使用自定义文本
          if (workflowEvent.message) {
            message = workflowEvent.message;
          }
          else if (workflowEvent.data?.text) {
            message = workflowEvent.data.text;
          }

          // 为node_started事件添加更多信息
          if (workflowEvent.event === 'node_started' && workflowEvent.data?.node_type) {
            message = `正在调用${workflowEvent.data.node_type}（${workflowEvent.data.node_name || workflowEvent.data.node_type}）`;
          }

          // 为node_finished事件添加更多信息
          if (workflowEvent.event === 'node_finished' && workflowEvent.data?.node_name) {
            message = `${workflowEvent.data.node_name}调用完毕`;
          }

          // 将事件信息存储到当前消息的workflowEvents数组中
          if (!lastItem.workflowEvents) {
            lastItem.workflowEvents = [];
          }

          lastItem.workflowEvents.push({
            type: workflowEvent.event,
            message,
            data: workflowEvent.data || {},
            dataCollapsed: true // 默认折叠事件数据
          });

          // 更新气泡项以触发渲染
          bubbleItems.value[bubbleItems.value.length - 1] = { ...lastItem };

  
        }
      },
      () => {
        // 流式响应完成，由DifyRenderer内部调用

        finalizeMessage();
      },
      (error: Error) => {
        // 处理解析错误
        console.error('Dify解析器错误:', error);
        ElMessage.error('消息解析出错：' + error.message);
        finalizeMessage();
      }
    );
  } catch (error) {
    console.error('处理数据块时出错:', error);
    ElMessage.error('处理消息时出错，请稍后重试');
  }
}

// 追加内容到消息并触发BubbleList更新
function appendContent(content: string) {
  const lastItem = bubbleItems.value[bubbleItems.value.length - 1];
  if (!lastItem || !content) return;

  const index = bubbleItems.value.length - 1;

  // 累积内容，实现平滑的流式效果
  lastItem.content = (lastItem.content || '') + content;
  // 保持typing为false，因为我们通过直接更新content来实现流式效果
  lastItem.typing = false;

  // 使用新对象确保响应式更新
  bubbleItems.value[index] = { ...lastItem };

  // 添加调试日志
  

  // 立即滚动到底部，确保用户实时看到内容
  bubbleListRef.value?.scrollToBottom();
}

// 完成消息处理 - 与BubbleList组件状态同步
function finalizeMessage() {
  const lastItem = bubbleItems.value[bubbleItems.value.length - 1];
  if (!lastItem) return;

  // 创建更新后的消息对象
  const updatedItem = {
    ...lastItem,
    loading: false,
    typing: false  // 关闭打字机效果
  };

  // 从工作流事件中解析总token和总花费
  
  if (lastItem.workflowEvents && lastItem.workflowEvents.length > 0) {
    let totalTokens = 0;
    let totalCost = 0;

    

    // 遍历所有工作流事件，查找token和花费信息
  lastItem.workflowEvents.forEach(event => {
    if (event.data) {
      // 特别关注workflow_finished事件，因为其中包含统计数据
      if (event.type === 'workflow_finished') {

        
        // 检查workflow_finished事件中的各种可能的统计数据位置
        // 检查顶层数据

        if (event.data.total_tokens) {
          totalTokens = parseInt(event.data.total_tokens) || 0;
          console.log('从workflow_finished.data.total_tokens提取:', event.data.total_tokens, '当前累计:', totalTokens);
        } else {
          console.log('workflow_finished.data中未找到total_tokens');
        }
        if (event.data.total_cost) {
          totalCost = parseFloat(event.data.total_cost) || 0;
          console.log('从workflow_finished.data.total_cost提取:', event.data.total_cost, '当前累计:', totalCost);
        } else {
          console.log('workflow_finished.data中未找到total_cost');
        }
          if (event.data.usage?.total_tokens) {
            totalTokens = parseInt(event.data.usage.total_tokens) || 0;
    
          }
          if (event.data.cost) {
            totalCost = parseFloat(event.data.cost) || 0;
    
          }
          
          // 检查process_data中的统计数据
          if (event.data.process_data?.usage?.total_tokens) {
            totalTokens = parseInt(event.data.process_data.usage.total_tokens) || 0;
    
          }
          if (event.data.process_data?.usage?.total_price) {
            totalCost = parseFloat(event.data.process_data.usage.total_price) || 0;
    
          }
          
          // 检查outputs中的统计数据
          if (event.data.outputs?.usage?.total_tokens) {
            totalTokens = parseInt(event.data.outputs.usage.total_tokens) || 0;
    
          }
          if (event.data.outputs?.usage?.total_price) {
            totalCost = parseFloat(event.data.outputs.usage.total_price) || 0;
    
          }
          
          // 检查execution_metadata中的统计数据
          if (event.data.execution_metadata?.total_tokens) {
            totalTokens = parseInt(event.data.execution_metadata.total_tokens) || 0;
    
          }
          if (event.data.execution_metadata?.total_price) {
            totalCost = parseFloat(event.data.execution_metadata.total_price) || 0;
    
          }
        }
        // 也检查其他事件中的token和花费信息
        if (event.data.usage?.total_tokens) {
          totalTokens += parseInt(event.data.usage.total_tokens) || 0;
        }
        if (event.data.usage?.prompt_tokens) {
          totalTokens += parseInt(event.data.usage.prompt_tokens) || 0;
        }
        if (event.data.usage?.completion_tokens) {
          totalTokens += parseInt(event.data.usage.completion_tokens) || 0;
        }
        if (event.data.cost) {
          totalCost += parseFloat(event.data.cost) || 0;
        }
        // 检查嵌套的数据结构
        if (event.data.result?.usage?.total_tokens) {
          totalTokens += parseInt(event.data.result.usage.total_tokens) || 0;
        }
        if (event.data.result?.cost) {
          totalCost += parseFloat(event.data.result.cost) || 0;
        }
        // 检查LLM节点特定的数据结构
        if (event.data.usage?.prompt_price) {
          totalCost += parseFloat(event.data.usage.prompt_price) || 0;
        }
        if (event.data.usage?.completion_price) {
          totalCost += parseFloat(event.data.usage.completion_price) || 0;
        }
        if (event.data.usage?.total_price) {
          totalCost = parseFloat(event.data.usage.total_price) || totalCost;
        }
      }
    });

    

    // 更新项目的token和花费信息
    if (totalTokens > 0) {
      updatedItem.totalTokens = totalTokens;
      
    }
    if (totalCost > 0) {
      updatedItem.totalCost = totalCost;
      
    }
    
  }

  // 更新气泡项以触发渲染
  const index = bubbleItems.value.length - 1;
  bubbleItems.value[index] = updatedItem;
  

  isThinking.value = false;

  // 最终滚动到底部，确保用户看到完整消息
  nextTick(() => {
    bubbleListRef.value?.scrollToBottom();
    // 添加延时检查，确保DOM更新后数据仍然存在
    setTimeout(() => {
      
    }, 100);
  });

  // 同步到存储，保持状态一致性
  syncToChatStore();
  
}

// 封装错误处理逻辑 - 确保错误信息也由AI回复显示
function handleError(err: any) {
  console.error('Fetch error:', err);
  
  // 获取错误消息
  let errorMessage = '发送消息失败，请稍后重试';
  if (err?.message?.includes('会话不存在') || err?.msg?.includes('会话不存在')) {
    errorMessage = '当前会话不存在，请刷新页面或创建新会话';
    // 可以选择清空当前会话ID，让用户重新开始
    if (route.params?.id !== 'not_login') {
      // 可以在这里添加创建新会话的逻辑
    }
  } else if (err?.message) {
    errorMessage = err.message;
  }
  
  // 显示错误提示
  ElMessage.error(errorMessage);
  
  // 将错误信息作为AI的回复显示在聊天界面中
  const lastItem = bubbleItems.value[bubbleItems.value.length - 1];
  if (lastItem && lastItem.role !== 'user') {
    // 更新最后一条AI消息为错误信息
    const index = bubbleItems.value.length - 1;
    bubbleItems.value[index] = {
      ...lastItem,
      content: `⚠️ ${errorMessage}`,
      loading: false,
      typing: false
    };
  } else {
    // 如果没有最近的AI消息，则添加一条新的错误消息
    addMessage(`⚠️ ${errorMessage}`, false);
  }
  
  // 确保消息处于完成状态
  finalizeMessage();
}

async function startSSE(chatContent: string) {
  try {
    // 检查会话ID是否有效
    const currentSessionId = route.params?.id !== 'not_login' ? String(route.params?.id) : undefined;

    // 检查智能体ID是否有效 - agent_id是必需参数
    const agentId = agentStore.currentAgentInfo?.agentId;
    if (!agentId) {
      ElMessage.error('请先选择一个AI助手');
      return;
    }

    // 添加用户输入的消息
    inputValue.value = '';
    addMessage(chatContent, true);
    addMessage('', false);

    // 滚动到底部
    bubbleListRef.value?.scrollToBottom();

    // 构建消息列表，包含完整的对话历史
    const userMessages = bubbleItems.value
      ?.filter((item: any) => item?.content && (item?.role === 'user' || item?.role === 'system'))
      ?.map((item: any) => ({
        role: item.role === 'system' ? 'assistant' : item.role,
        content: item.content,
      })) || [];

    // 如果没有任何消息，不发送请求
    if (userMessages.length === 0) {
      ElMessage.warning('请输入消息内容');
      return;
    }

    // 构建SendDTO参数 - agent_id是必需参数
    const sendData: SendDTO = {
      messages: userMessages,
      userId: userStore.userInfo?.userId,
      agent_id: String(agentId), // agent_id是必需参数，确保始终传递
      stream: true, // 启用流式响应
      usingContext: true, // 默认携带上下文, // 默认携带上下文
    };

    // 只要sessionId存在且不是'not_login'就添加
    if (currentSessionId && currentSessionId !== 'not_login') {
      sendData.sessionId = currentSessionId;
    }

    // 使用原生Fetch API处理SSE流，避免hook-fetch的缓冲
    try {
      const response = await fetch(`/dev-api/chat/send`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userStore.token}`
        },
        body: JSON.stringify(sendData)
      });

      if (!response.ok || !response.body) {
        throw new Error('SSE连接失败');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // 重置DifyRenderer状态
      difyRenderer.reset();

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // 通知DifyRenderer流已结束
          difyRenderer.notifyEnd();
          break;
        }

        // 立即处理每个数据块，避免buffer累积
        const chunkData = decoder.decode(value, { stream: true });

        // 将原始数据块传递给handleDataChunk，让DifyRenderer内部处理SSE格式
        handleDataChunk(chunkData);
      }
    } catch (error) {
      console.error('SSE流处理错误:', error);
      handleError(error);
    }
  }
  catch (err) {
    handleError(err);
  }
  finally {

    // 确保消息完成状态 - 使用统一的finalizeMessage处理
    finalizeMessage();
  }
}

// 中断请求
async function cancelSSE() {
  cancel();
  // 使用统一的完成处理
  finalizeMessage();
}

// 添加消息 - 维护聊天记录，确保与BubbleList组件兼容
function addMessage(message: string, isUser: boolean) {
  // 确保bubbleItems.value是数组
  if (!Array.isArray(bubbleItems.value)) {
    bubbleItems.value = [];
  }

  const i = bubbleItems.value.length;
  const obj: MessageItem = {
    key: i,
    avatar: isUser
      ? avatar.value
      : new URL('@/assets/images/logo.png', import.meta.url).href,
    avatarSize: '32px',
    role: isUser ? 'user' : 'system',
    placement: isUser ? 'end' : 'start',
    isMarkdown: !isUser,
    loading: false,  // 移除Loading状态，避免阻塞数据流更新
    content: message || '',
    reasoning_content: '',
    thinkingStatus: 'start',
    thinlCollapse: false,
    noStyle: !isUser,
    workflowEvents: [], // 初始化工作流事件数组
    workflowEventsCollapsed: false, // 默认展开工作流事件
    // 移除打字机效果，直接显示流式内容
    typing: false,
    // 添加消息时间戳
    timestamp: new Date().toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    })
  };
  bubbleItems.value.push(obj);

  // 确保BubbleList立即响应新消息
  nextTick(() => {
    bubbleListRef.value?.scrollToBottom();
  });

  // 同步到chatStore
  syncToChatStore();
}

// 同步消息到chatStore
function syncToChatStore() {
  const currentSessionId = route.params?.id;
  if (currentSessionId && currentSessionId !== 'not_login') {
    chatStore.chatMap[String(currentSessionId)] = [...bubbleItems.value];
  }
}

// 展开收起 事件展示
function handleChange(payload: { value: boolean; status: ThinkingStatus }) {
  
}

// 切换单个事件数据的展开/折叠状态
function toggleEventData(item: MessageItem, eventIndex: number) {
  nextTick(() => {
    const index = bubbleItems.value.findIndex(i => i.key === item.key);
    if (index !== -1 && bubbleItems.value[index].workflowEvents && bubbleItems.value[index].workflowEvents[eventIndex]) {
      // 创建新对象以确保响应式系统检测到变化
      const updatedItem = {
        ...bubbleItems.value[index],
        workflowEvents: [...bubbleItems.value[index].workflowEvents]
      };

      // 切换数据折叠状态
      updatedItem.workflowEvents[eventIndex] = {
        ...updatedItem.workflowEvents[eventIndex],
        dataCollapsed: !updatedItem.workflowEvents[eventIndex].dataCollapsed
      };

      bubbleItems.value[index] = updatedItem;
    }
  });
}

// 切换整个工作流事件区域的展开/折叠状态
function toggleWorkflowEvents(item: MessageItem) {
  const currentItems = bubbleItems.value;
  const index = currentItems.findIndex(i => i.key === item.key);
  if (index !== -1) {
    // 创建新数组和新对象确保响应式系统检测到变化
    const updatedItems = [...currentItems];
    updatedItems[index] = {
      ...updatedItems[index],
      workflowEventsCollapsed: !updatedItems[index].workflowEventsCollapsed
    };
    bubbleItems.value = updatedItems;
  }
}

// BubbleList组件的更新钩子，确保数据更新时触发组件渲染
function handleBubbleListUpdate() {
  // 当数据更新时，可以执行额外的逻辑
  
  // 滚动到底部，确保用户看到最新内容
  bubbleListRef.value?.scrollToBottom();
}

function handleDeleteCard(_item: FilesCardProps, index: number) {
  filesStore.deleteFileByIndex(index);
}

watch(
  () => filesStore.filesList.length,
  (val) => {
    if (val > 0) {
      nextTick(() => {
        senderRef.value?.openHeader();
      });
    }
    else {
      nextTick(() => {
        senderRef.value?.closeHeader();
      });
    }
  },
);
</script>

<template>
  <div class="chat-with-id-container">
    <div class="chat-warp">
      <BubbleList ref="bubbleListRef" :list="bubbleItems" max-height="calc(100vh - 240px)"
        @update:list="handleBubbleListUpdate">
        <template #header="{ item }">
          <Thinking v-if="item.reasoning_content" v-model="item.thinlCollapse" :content="item.reasoning_content"
            :status="item.thinkingStatus" class="thinking-chain-warp" @change="handleChange" />

          <!-- 工作流事件展示区域 -->
          <div v-if="item.workflowEvents && item.workflowEvents.length > 0" class="workflow-events-container">
            <div class="workflow-events-toggle" @click="toggleWorkflowEvents(item)">
              <span class="workflow-events-label">
                {{ item.workflowEventsCollapsed ? '▼' : '▲' }} 工作流事件 ({{ item.workflowEvents.length }})
              </span>
            </div>

            <div v-if="!item.workflowEventsCollapsed" class="workflow-events-content">
              <div v-for="(event, index) in item.workflowEvents" :key="index" class="workflow-event-item">
                <div class="event-header">
                  <span class="event-type">{{ event.type }}:</span>
                  <span class="event-message">{{ event.message }}</span>
                  <span v-if="Object.keys(event.data).length > 0" class="event-data-toggle"
                    @click.stop="toggleEventData(item, index)">
                    {{ event.dataCollapsed ? '▼' : '▲' }}
                  </span>
                </div>
                <div v-if="Object.keys(event.data).length > 0 && !event.dataCollapsed" class="event-data">
                  {{ JSON.stringify(event.data) }}
                </div>
              </div>
            </div>
          </div>
        </template>

        <template #content="{ item }">
          <!-- chat 内容走 markdown -->
          <XMarkdown v-if="item.content && item.role === 'system'" :markdown="item.content" class="markdown-body"
            :themes="{ light: 'github-light', dark: 'github-dark' }" default-theme-mode="dark" />
          <!-- user 内容 纯文本 -->
          <div v-if="item.content && item.role === 'user'" class="user-content">
            {{ item.content }}
          </div>
          
          <!-- 显示token和花费统计信息 -->
          <div v-if="((item.totalTokens || 0) > 0 || (item.totalCost || 0) > 0) && item.role === 'system'" class="token-cost-info">
            <span v-if="item.totalTokens" class="token-count">
              📊 Token: {{ item.totalTokens }}
            </span>
            <span v-if="item.totalCost" class="cost-amount">
              💰 花费: ¥{{ item.totalCost.toFixed(4) }}
            </span>
            <span v-if="item.timestamp" class="message-time">
              ⏰ 时间: {{ item.timestamp }}
            </span>
          </div>
          <!-- 对于用户消息和没有统计数据的系统消息，单独显示时间 -->
          <div v-else-if="item.timestamp" class="message-time-only">
            ⏰ 时间: {{ item.timestamp }}
          </div>
          <!-- 调试用：始终显示一些模拟的统计数据 -->
          <div class="debug-token-cost-info">
            <span class="debug-token-count">
              🔧 调试 Token: 100
            </span>
            <span class="debug-cost-amount">
              🔧 调试花费: ¥0.0050
            </span>
          </div>
        </template>
      </BubbleList>

      <Sender ref="senderRef" v-model="inputValue" class="chat-defaul-sender" :auto-size="{
        maxRows: 6,
        minRows: 2,
      }" variant="updown" clearable allow-speech :loading="isLoading" @submit="startSSE" @cancel="cancelSSE">
        <template #header>
          <div class="sender-header p-12px pt-6px pb-0px">
            <Attachments :items="filesStore.filesList" :hide-upload="true" @delete-card="handleDeleteCard">
              <template #prev-button="{ show, onScrollLeft }">
                <div v-if="show"
                  class="prev-next-btn left-8px flex-center w-22px h-22px rounded-8px border-1px border-solid border-[rgba(0,0,0,0.08)] c-[rgba(0,0,0,.4)] hover:bg-#f3f4f6 bg-#fff font-size-10px"
                  @click="onScrollLeft">
                  <el-icon>
                    <ArrowLeftBold />
                  </el-icon>
                </div>
              </template>

              <template #next-button="{ show, onScrollRight }">
                <div v-if="show"
                  class="prev-next-btn right-8px flex-center w-22px h-22px rounded-8px border-1px border-solid border-[rgba(0,0,0,0.08)] c-[rgba(0,0,0,.4)] hover:bg-#f3f4f6 bg-#fff font-size-10px"
                  @click="onScrollRight">
                  <el-icon>
                    <ArrowRightBold />
                  </el-icon>
                </div>
              </template>
            </Attachments>
          </div>
        </template>
        <template #prefix>
          <div class="flex-1 flex items-center gap-8px flex-none w-fit overflow-hidden">
            <FilesSelect />
            <ModelSelect />
          </div>
        </template>
      </Sender>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chat-with-id-container {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;

  /* 移除最大宽度限制，使工作流事件可以达到100%宽度 */

  /* max-width: 800px; */
  height: 100%;
  .chat-warp {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    width: 100%;
    height: calc(100vh - 60px);
    .thinking-chain-warp {
      margin-bottom: 12px;
    }
  }
  :deep() {
    .el-bubble-list {
      padding-top: 24px;
    }
    .el-bubble {
      padding: 0 12px;
      padding-bottom: 24px;
    }
    .el-typewriter {
      overflow: hidden;
      border-radius: 12px;
    }
    .user-content {
      // 换行
      white-space: pre-wrap;
    }
    .markdown-body {
      background-color: transparent;
    }
    .markdown-elxLanguage-header-div {
      top: -25px !important;
    }

    // xmarkdown 样式
    .elx-xmarkdown-container {
      padding: 8px 4px;
    }

    // 工作流事件样式 - 确保整个工作事件流始终保持100%宽度
    .workflow-events-container {
      display: block;
      width: 100% !important;
      max-width: 100% !important;
      margin-top: 12px;
      overflow: hidden;
      background-color: #f9fafb;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgb(0 0 0 / 10%);
      transition: all 0.3s ease;
    }
    .workflow-events-toggle {
      box-sizing: border-box;
      display: block;

      /* 确保标题栏始终保持100%宽度 */
      width: 100% !important;
      padding: 12px 16px;
      cursor: pointer;
      background-color: #f3f4f6;
      border-bottom: 1px solid #e5e7eb;
      transition: background-color 0.3s ease;
    }
    .workflow-events-toggle:hover {
      background-color: #e5e7eb;
    }
    .workflow-events-label {
      display: flex;
      gap: 8px;
      align-items: center;
      font-size: 14px;
      font-weight: 500;
      color: #374151;
    }
    .workflow-events-content {
      box-sizing: border-box;
      display: block;

      /* 确保内容区域也保持100%宽度 */
      width: 100% !important;
      max-height: 400px;
      padding: 0;
      overflow-y: auto;
    }
    .workflow-event-item {
      box-sizing: border-box;
      display: block;
      width: 100%;
      padding: 16px;
      border-bottom: 1px solid #e5e7eb;
      transition: background-color 0.2s ease;
    }
    .workflow-event-item:last-child {
      border-bottom: none;
    }
    .workflow-event-item:hover {
      background-color: rgb(0 0 0 / 2%);
    }
    .event-header {
      box-sizing: border-box;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: flex-start;
      width: 100%;
    }
    .event-type {
      font-size: 13px;
      font-weight: 600;
      color: #111827;
    }
    .event-message {
      flex: 1;
      font-size: 13px;
      line-height: 1.4;
      color: #4b5563;
    }
    .event-data-toggle {
      padding: 2px 6px;
      font-size: 12px;
      color: #6b7280;
      cursor: pointer;
      border-radius: 4px;
      transition: all 0.2s ease;
    }
    .event-data-toggle:hover {
      color: #374151;
      background-color: #e5e7eb;
    }
    .event-data {
      box-sizing: border-box;
      display: block;

      /* 确保数据展示区域不会导致容器宽度变化 */
      width: 100% !important;
      padding: 12px;
      margin-top: 8px;
      overflow-x: auto;
      font-family: Monaco, Menlo, 'Ubuntu Mono', monospace;
      font-size: 12px;
      line-height: 1.5;
      color: #111827;
      word-break: break-all;
      word-wrap: break-word;

      /* 优化长文本的处理方式 */
      white-space: pre-wrap;
      background-color: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
    }

    // 滚动条样式优化
    .workflow-events-content::-webkit-scrollbar {
      width: 6px;
    }
    .workflow-events-content::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    .workflow-events-content::-webkit-scrollbar-thumb {
      background: #c1c1c1;
      border-radius: 3px;
    }
    .workflow-events-content::-webkit-scrollbar-thumb:hover {
      background: #a1a1a1;
    }
    .event-data::-webkit-scrollbar {
      height: 6px;
    }
    .event-data::-webkit-scrollbar-track {
      background: #f1f1f1;
    }
    .event-data::-webkit-scrollbar-thumb {
      background: #c1c1c1;
      border-radius: 3px;
    }
    .event-data::-webkit-scrollbar-thumb:hover {
      background: #a1a1a1;
    }
    
    // Token和花费信息样式
    .token-cost-info {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      padding: 8px 12px;
      margin-top: 8px;
      font-size: 12px;
      color: #6b7280;
      background-color: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
    }
    .token-count,
    .cost-amount,
    .message-time {
      display: flex;
      gap: 4px;
      align-items: center;
    }
    .message-time-only {
      padding: 8px 12px;
      margin-top: 8px;
      font-size: 12px;
      color: #6b7280;
      text-align: right;
    }
  }
  .chat-defaul-sender {
    width: 100%;
    margin-bottom: 22px;
  }
}
</style>
