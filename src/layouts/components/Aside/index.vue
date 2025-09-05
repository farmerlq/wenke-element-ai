<!-- Aside 侧边栏 -->
<script setup lang="ts">
import type { ConversationItem } from 'vue-element-plus-x/types/Conversations';
import type { ChatSessionVo } from '@/api/session/types';
import { useRoute, useRouter } from 'vue-router';
import { get_session } from '@/api';
import logo from '@/assets/images/logo.png';
import SvgIcon from '@/components/SvgIcon/index.vue';
import Collapse from '@/layouts/components/Header/components/Collapse.vue';
import { useDesignStore } from '@/stores';
import { useSessionStore } from '@/stores/modules/session';
import { useUserStore } from '@/stores/modules/user';
import { computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { User, Plus } from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();
const designStore = useDesignStore();
const sessionStore = useSessionStore();
const userStore = useUserStore();

// 用户信息
const userName = computed(() => userStore.userInfo?.nickName || userStore.userInfo?.username || '未登录');
const userRole = computed(() => userStore.userInfo?.roles?.[0]?.roleName || '未知角色');
const userAvatar = computed(() => userStore.userInfo?.avatar || new URL('@/assets/images/logo.png', import.meta.url).href);

const handleUserMenuClick = (item: any) => {
  const key = item.key;
  switch (key) {
    case 'login':
      router.push('/login');
      break;
    case '1':
    case '2':
      ElMessage.info('功能暂未开放');
      break;
    case '4':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        userStore.logout().then(() => {
          router.push('/login');
        });
      }).catch(() => {
        // 取消退出
      });
      break;
    default:
      break;
  }
};

const handleAvatarError = () => {
  // 头像加载失败时，使用本地logo
  if (userStore.userInfo) {
    userStore.userInfo.avatar = new URL('@/assets/images/logo.png', import.meta.url).href;
  }
};

const sessionId = computed(() => route.params?.id);
const conversationsList = computed(() => sessionStore.sessionList);
const loadMoreLoading = computed(() => sessionStore.isLoadingMore);
const active = ref<string | undefined>();

onMounted(async () => {
  // 只有在用户已登录时才获取会话列表
  if (userStore.token) {
    await sessionStore.requestSessionList();
    // 高亮最新会话
    if (conversationsList.value.length > 0 && sessionId.value) {
      const currentSessionRes = await get_session(`${sessionId.value}`);
      // 通过 ID 查询详情，设置当前会话 (因为有分页)
      sessionStore.setCurrentSession(currentSessionRes.data);
    }
  }
});

watch(
  () => sessionStore.currentSession,
  (newValue) => {
    active.value = newValue ? `${newValue.id}` : undefined;
  },
);

// 创建会话
function handleCreatChat() {
  // 创建会话, 跳转到默认聊天
  sessionStore.createSessionBtn();
}

// 切换会话
function handleChange(item: ConversationItem<ChatSessionVo>) {
  sessionStore.setCurrentSession(item);
  router.replace({
    name: 'chatWithId',
    params: {
      id: item.id,
    },
  });
}

// 处理组件触发的加载更多事件
async function handleLoadMore() {
  if (!sessionStore.hasMore)
    return; // 无更多数据时不加载
  await sessionStore.loadMoreSessions();
}

// 右键菜单
function handleMenuCommand(command: string, item: ConversationItem<ChatSessionVo>) {
  switch (command) {
    case 'delete':
      ElMessageBox.confirm('删除后，聊天记录将不可恢复。', '确定删除对话？', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
        cancelButtonClass: 'el-button--info',
        roundButton: true,
        autofocus: false,
      })
        .then(() => {
          // 删除会话
          sessionStore.deleteSessions([item.id!]);
          nextTick(() => {
            if (item.id === active.value) {
              // 如果删除当前会话 返回到默认页
              sessionStore.createSessionBtn();
            }
          });
        })
        .catch(() => {
          // 取消删除
        });
      break;
    case 'rename':
      ElMessageBox.prompt('', '编辑对话名称', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputErrorMessage: '请输入对话名称',
        confirmButtonClass: 'el-button--primary',
        cancelButtonClass: 'el-button--info',
        roundButton: true,
        inputValue: item.sessionTitle, // 设置默认值
        autofocus: false,
        inputValidator: (value) => {
          if (!value) {
            return false;
          }
          return true;
        },
      }).then(({ value }) => {
        sessionStore
          .updateSession({
            id: item.id!,
            sessionTitle: value,
            sessionContent: item.sessionContent,
          })
          .then(() => {
            ElMessage({
              type: 'success',
              message: '修改成功',
            });
            nextTick(() => {
              // 如果是当前会话，则更新当前选中会话信息
              if (sessionStore.currentSession?.id === item.id) {
                sessionStore.setCurrentSession({
                  ...item,
                  sessionTitle: value,
                });
              }
            });
          });
      });
      break;
    default:
      break;
  }
}
</script>

<template>
  <div
    class="aside-container"
    :class="{
      'aside-container-suspended': designStore.isSafeAreaHover,
      'aside-container-collapse': designStore.isCollapse,
      // 折叠且未激活悬停时添加 no-delay 类
      'no-delay': designStore.isCollapse && !designStore.hasActivatedHover,
    }"
  >
    <div class="aside-wrapper">
      <div v-if="!designStore.isCollapse" class="aside-header">
        <div class="flex items-center gap-8px hover:cursor-pointer" @click="handleCreatChat">
          <el-image :src="logo" alt="logo" fit="cover" class="logo-img" />
          <span class="logo-text max-w-150px text-overflow">Element Plus X</span>
        </div>
        <Collapse class="ml-auto" />
      </div>

      <div class="aside-body">
        <div class="creat-chat-btn-wrapper">
          <div class="creat-chat-btn" @click="handleCreatChat">
            <el-icon class="add-icon">
              <Plus />
            </el-icon>
            <span class="creat-chat-text">新对话</span>
            <SvgIcon name="ctrl+k" size="37" />
          </div>
        </div>

        <div class="aside-content">
          <div v-if="conversationsList.length > 0" class="conversations-wrap overflow-hidden">
            <Conversations
              v-model:active="active"
              :items="conversationsList"
              :label-max-width="200"
              :show-tooltip="true"
              :tooltip-offset="60"
              show-built-in-menu
              groupable
              row-key="id"
              label-key="sessionTitle"
              tooltip-placement="right"
              :load-more="handleLoadMore"
              :load-more-loading="loadMoreLoading"
              :items-style="{
                marginLeft: '8px',
                userSelect: 'none',
                borderRadius: '10px',
                padding: '8px 12px',
              }"
              :items-active-style="{
                backgroundColor: '#fff',
                boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
                color: 'rgba(0, 0, 0, 0.85)',
              }"
              :items-hover-style="{
                backgroundColor: 'rgba(0, 0, 0, 0.04)',
              }"
              @menu-command="handleMenuCommand"
              @change="handleChange"
            />
          </div>

          <el-empty v-else class="h-full flex-center" description="暂无对话记录" />
        </div>

        <!-- 用户账号信息 -->
        <div class="user-account-section">
          <!-- 未登录状态 -->
          <div v-if="!userStore.token" class="login-section">
            <el-button 
              type="primary" 
              class="w-full" 
              @click="handleUserMenuClick({ key: 'login' })"
            >
              登录账号
            </el-button>
          </div>
          
          <!-- 已登录状态 -->
          <el-dropdown v-else trigger="click" placement="top-start" :offset="4">
            <div class="user-info cursor-pointer">
              <el-avatar :size="32" :src="userAvatar" class="user-avatar" @error="handleAvatarError">
                <el-icon><User /></el-icon>
              </el-avatar>
              <div class="user-details">
                <span class="user-name">{{ userName }}</span>
                <span class="user-role">{{ userRole }}</span>
              </div>
            </div>
            
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleUserMenuClick({ key: '1' })">
                  <SvgIcon name="settings-4-fill" size="16" class-name="mr-8px" />
                  个人设置
                </el-dropdown-item>
                <el-dropdown-item @click="handleUserMenuClick({ key: '2' })">
                  <SvgIcon name="user-3-fill" size="16" class-name="mr-8px" />
                  账号信息
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleUserMenuClick({ key: '4' })">
                  <SvgIcon name="logout-box-r-line" size="16" class-name="mr-8px" />
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <!-- 版本信息 -->
        <div class="aside-footer">
          <span class="footer-text">版本 1.0.0</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
// 基础样式
.aside-container {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 11;
  width: var(--sidebar-default-width);
  height: 100%;
  pointer-events: auto;
  background-color: var(--sidebar-background-color);
  border-right: 0.5px solid var(--s-color-border-tertiary, rgb(0 0 0 / 8%));
  .aside-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;

    // 侧边栏头部样式
    .aside-header {
      display: flex;
      align-items: center;
      height: 36px;
      margin: 10px 12px 0;
      .logo-img {
        box-sizing: border-box;
        width: 36px;
        height: 36px;
        padding: 4px;
        overflow: hidden;
        background-color: #ffffff;
        border-radius: 50%;
        img {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
        }
      }
      .logo-text {
        font-size: 16px;
        font-weight: 700;
        color: rgb(0 0 0 / 85%);
        transform: skewX(-2deg);
      }
    }

    // 侧边栏内容样式
    .aside-body {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 0;

      .creat-chat-btn-wrapper {
        padding: 0 12px;
        .creat-chat-btn {
          display: flex;
          gap: 6px;
          align-items: center;
          padding: 8px 6px;
          margin-top: 16px;
          margin-bottom: 6px;
          color: #0057ff;
          cursor: pointer;
          user-select: none;
          background-color: rgb(0 87 255 / 6%);
          border: 1px solid rgb(0 102 255 / 15%);
          border-radius: 12px;
          &:hover {
            background-color: rgb(0 87 255 / 12%);
          }
          .creat-chat-text {
            font-size: 14px;
            font-weight: 700;
            line-height: 22px;
          }
          .add-icon {
            width: 24px;
            height: 24px;
            font-size: 16px;
          }
          .svg-icon {
            height: 24px;
            margin-left: auto;
            color: rgb(0 87 255 / 30%);
          }
        }
      }
      .aside-content {
        display: flex;
        flex: 1;
        flex-direction: column;
        height: 100%;
        min-height: 0;

        // 会话列表高度-基础样式
        .conversations-wrap {
          height: calc(100vh - 180px);
          .label {
            display: flex;
            align-items: center;
            height: 100%;
          }
        }
      }

      // 用户账号信息样式
      .user-account-section {
        padding: 12px;
        margin-top: auto;
        border-top: 1px solid var(--s-color-border-tertiary, rgb(0 0 0 / 8%));
        
        .user-info {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px;
          border-radius: 8px;
          cursor: pointer;
          transition: background-color 0.2s;

          &:hover {
            background-color: rgba(0, 0, 0, 0.02);
          }
          
          .user-avatar {
            flex-shrink: 0;
          }
          
          .user-details {
            display: flex;
            flex-direction: column;
            min-width: 0;
            
            .user-name {
              font-size: 14px;
              font-weight: 500;
              color: rgba(0, 0, 0, 0.85);
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }
            
            .user-role {
              font-size: 12px;
              color: rgba(0, 0, 0, 0.45);
              white-space: nowrap;
              overflow: hidden;
              text-overflow: ellipsis;
            }
          }
        }
      }

      // 版本信息样式
      .aside-footer {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 8px 12px;
        border-top: 1px solid var(--s-color-border-tertiary, rgb(0 0 0 / 8%));
        
        .footer-text {
          font-size: 12px;
          color: rgba(0, 0, 0, 0.45);
        }
      }
    }
  }
}

// 折叠样式
.aside-container-collapse {
  position: absolute;
  top: 54px;
  z-index: 22;
  height: auto;
  max-height: calc(100% - 110px);
  padding-bottom: 12px;
  overflow: hidden;

  /* 禁用悬停事件 */
  pointer-events: none;
  border: 1px solid rgb(0 0 0 / 8%);
  border-radius: 15px;
  box-shadow:
    0 10px 20px 0 rgb(0 0 0 / 10%),
    0 0 1px 0 rgb(0 0 0 / 15%);
  opacity: 0;

  // 指定样式过渡

  // 向左偏移一个宽度
  transform: translateX(-100%);
  transition: opacity 0.3s ease 0.3s, transform 0.3s ease 0.3s;

  /* 新增：未激活悬停时覆盖延迟 */
  &.no-delay {
    transition-delay: 0s, 0s;
  }
}

// 悬停样式
.aside-container-collapse:hover,
.aside-container-collapse.aside-container-suspended {
  height: auto;
  max-height: calc(100% - 110px);
  padding-bottom: 12px;
  overflow: hidden;
  pointer-events: auto;
  border: 1px solid rgb(0 0 0 / 8%);
  border-radius: 15px;
  box-shadow:
    0 10px 20px 0 rgb(0 0 0 / 10%),
    0 0 1px 0 rgb(0 0 0 / 15%);

  // 直接在这里写悬停时的样式（与 aside-container-suspended 一致）
  opacity: 1;

  // 过渡动画沿用原有设置
  transform: translateX(15px);
  transition: opacity 0.3s ease 0s, transform 0.3s ease 0s;

  // 会话列表高度-悬停样式
  .conversations-wrap {
    height: calc(100vh - 225px) !important;
  }
}

// 样式穿透
:deep() {
  // 会话列表背景色
  .conversations-list {
    background-color: transparent !important;
  }

  // 群组标题样式 和 侧边栏菜单背景色一致
  .conversation-group-title {
    padding-left: 12px !important;
    background-color: var(--sidebar-background-color) !important;
  }
}
</style>
