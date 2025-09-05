import type {
  ChatSessionVo,
  CreateSessionDTO,
  // CreateSessionVO,
  GetSessionListParams,
} from './types';
import { del, get, post, put } from '@/utils/request';

export function get_session_list(params?: GetSessionListParams) {
  return get<{
    data: {
      list: ChatSessionVo[];
      total: number;
    };
  }>('/system/session/list', params).json().then(res => ({
    data: {
      rows: res.data?.list || [],
      total: res.data?.total || 0
    }
  }));
}

// 从会话列表中获取单个会话详情
export function get_session(sessionId: string) {
  return get_session_list().then(res => {
    const session = res.data.rows.find((s: ChatSessionVo) => s.id === sessionId);
    if (!session) {
      // 返回空会话而不是抛出错误，让调用方处理
      return { data: null };
    }
    return { data: session };
  });
}

export function create_session(data: CreateSessionDTO) {
  return post('/system/session', data).json();
}

export function update_session(data: ChatSessionVo) {
  return put('/system/session', data).json();
}

export function delete_session(session_id: string | number) {
  return del(`/system/session/${session_id}`).json();
}
