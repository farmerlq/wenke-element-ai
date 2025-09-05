import type { LoginUser, LoginDTO } from '@/api/auth/types';
import { defineStore } from 'pinia';
import { useRouter } from 'vue-router';
import { login as apiLogin, getUserInfo as apiGetUserInfo, logout as apiLogout } from '@/api/auth';
import { ElMessage } from 'element-plus';

export const useUserStore = defineStore(
  'user',
  () => {
    const token = ref<string>();
    const router = useRouter();
    const setToken = (value: string) => {
      token.value = value;
    };
    const clearToken = () => {
      token.value = void 0;
    };

    const userInfo = ref<LoginUser>();
    const setUserInfo = (value: LoginUser) => {
      userInfo.value = value;
    };
    const clearUserInfo = () => {
      userInfo.value = void 0;
    };

    const logout = async () => {
      try {
        await apiLogout();
      } catch (error) {
        console.error('登出失败:', error);
      } finally {
        clearToken();
        clearUserInfo();
        router.replace({ name: 'login' });
      }
    };

    const login = async (username: string, password: string) => {
      try {
        const loginData: LoginDTO = { username, password };
        const response = await apiLogin(loginData);
        
        if (response.code === 200 && response.data?.access_token) {
          setToken(response.data.access_token);
          
          // 获取用户信息
          const userInfoResponse = await apiGetUserInfo();
          if (userInfoResponse.code === 200) {
            // 设置默认头像
            if (!userInfoResponse.data.avatar) {
              userInfoResponse.data.avatar = new URL('@/assets/images/logo.png', import.meta.url).href;
            }
            setUserInfo(userInfoResponse.data);
          }
          
          ElMessage.success('登录成功');
          return { success: true };
        } else {
          ElMessage.error(response.msg || '登录失败');
          return { success: false, message: response.msg || '登录失败' };
        }
      } catch (error) {
        ElMessage.error('登录失败，请检查网络连接');
        return { success: false, message: '网络错误' };
      }
    };

    // 新增：登录弹框状态
    const isLoginDialogVisible = ref(false);

    // 新增：打开弹框方法
    const openLoginDialog = () => {
      isLoginDialogVisible.value = true;
    };

    // 新增：关闭弹框方法（可根据需求扩展）
    const closeLoginDialog = () => {
      isLoginDialogVisible.value = false;
    };

    return {
      token,
      setToken,
      clearToken,
      userInfo,
      setUserInfo,
      clearUserInfo,
      logout,
      login,
      // 新增：暴露弹框状态和方法
      isLoginDialogVisible,
      openLoginDialog,
      closeLoginDialog,
    };
  },
  {
    persist: true,
  },
);
