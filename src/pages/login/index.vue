<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <img src="/favicon.ico" alt="Logo" class="logo" />
        <h1>AI智能对话系统</h1>
        <p>请登录后开始使用</p>
      </div>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p>演示账号：admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores'

const router = useRouter()
const userStore = useUserStore()

const loginFormRef = ref()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    loading.value = true
    try {
      const result = await userStore.login(loginForm.username, loginForm.password)
      if (result.success) {
        ElMessage.success('登录成功！')
        router.push('/chat')
      } else {
        ElMessage.error(result.message || '用户名或密码错误！')
      }
    } catch (error) {
      ElMessage.error('登录失败，请重试！')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped lang="scss">
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  
  .login-box {
    width: 400px;
    padding: 40px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    
    .login-header {
      text-align: center;
      margin-bottom: 30px;
      
      .logo {
        width: 60px;
        height: 60px;
        margin-bottom: 10px;
      }
      
      h1 {
        margin: 0 0 10px;
        font-size: 24px;
        color: #333;
      }
      
      p {
        margin: 0;
        color: #666;
        font-size: 14px;
      }
    }
    
    .login-form {
      margin-bottom: 20px;
    }
    
    .login-footer {
      text-align: center;
      
      p {
        margin: 0;
        color: #999;
        font-size: 12px;
      }
    }
  }
}
</style>