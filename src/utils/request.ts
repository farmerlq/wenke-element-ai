import type { HookFetchPlugin } from 'hook-fetch';
import { ElMessage } from 'element-plus';
import hookFetch from 'hook-fetch';
import { sseTextDecoderPlugin } from 'hook-fetch/plugins';
import router from '@/routers';

interface BaseResponse {
  code: number;
  data: never;
  msg: string;
  rows: never;
}

function jwtPlugin(): HookFetchPlugin<BaseResponse> {
  return {
    name: 'jwt',
    beforeRequest: async (config) => {
      // 延迟获取store，避免初始化顺序问题
      const { useUserStore } = await import('@/stores');
      const userStore = useUserStore();

      config.headers = new Headers(config.headers);
      if (userStore.token) {
        config.headers.set('Authorization', `Bearer ${userStore.token}`);
      }
      return config;
    },
    afterResponse: async (response) => {
    
      if (response.result?.code === 200) {
        return response;
      }

      // 处理HTTP状态码
      const status = response.response?.status;

      // 处理403逻辑
      if (status === 403 || response.result?.code === 403) {
        // 跳转到403页面（确保路由已配置）
        router.replace({
          name: '403',
        });
        ElMessage.error(response.result?.msg || '权限不足');
        return Promise.reject(response);
      }
      // 处理401逻辑
      if (status === 401 || response.result?.code === 401) {
        // 如果没有权限，跳转到登录页面
        const { useUserStore } = await import('@/stores');
        const userStore = useUserStore();
        userStore.logout();
        router.replace({
          name: 'login',
        });
        ElMessage.error(response.result?.msg || '未授权，请重新登录');
        return Promise.reject(response);
      }
      ElMessage.error(response.result?.msg || '请求失败');
      return Promise.reject(response);
    },
  };
}

export const request = hookFetch.create<BaseResponse, 'data' | 'rows'>({
  baseURL: import.meta.env.VITE_WEB_BASE_API,
  headers: {
    'Content-Type': 'application/json',
  },
  plugins: [sseTextDecoderPlugin({ json: true, prefix: 'data:'}), jwtPlugin()],
});

export const post = request.post;

export const get = request.get;

export const put = request.put;

export const del = request.delete;

export default request;
