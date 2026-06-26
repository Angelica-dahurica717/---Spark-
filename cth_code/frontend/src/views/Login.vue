<!-- 登录页。表单验证 → Axios 调用登录接口 → 成功后存储 token/username/role 到 localStorage → 跳转首页 -->

<template>
  <div class="login-container">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>谣言分析系统</h2>
          <p>Rumor Hotspot Analysis System</p>
        </div>
      </template>

      <el-form ref="loginFormRef" :model="loginForm" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="请输入用户名" 
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码" 
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item style="margin-bottom: 0;">
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登录系统
          </el-button>
          <el-button class="register-btn" @click="registerDialogVisible = true">
            注册账号
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="hint">
        <p>测试账号：admin / admin123</p>
      </div>
    </el-card>

    <!-- 注册弹窗 -->
    <el-dialog v-model="registerDialogVisible" title="用户注册" width="400px">
      <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" placeholder="请输入英文或数字" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="registerForm.password" type="password" placeholder="请输入英文或数字" show-password />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="registerForm.name" placeholder="请输入真实姓名或昵称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="registerDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="registerLoading" @click="handleRegister">确定注册</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const registerDialogVisible = ref(false)
const registerFormRef = ref(null)
const registerLoading = ref(false)
const registerForm = reactive({
  username: '',
  password: '',
  name: ''
})
const registerRules = reactive({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }]
})

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = reactive({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
})

const handleLogin = () => {
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const res = await axios.post('/api/auth/login', loginForm)
        if (res.data.code === 200) {
          ElMessage.success('登录成功')
          sessionStorage.setItem('token', res.data.data.token)
          sessionStorage.setItem('username', res.data.data.username)
          sessionStorage.setItem('role', res.data.data.role)
          sessionStorage.setItem('name', res.data.data.name)
          router.push('/')
        } else {
          ElMessage.error(res.data.msg || '登录失败')
        }
      } catch (error) {
        if(error.response && error.response.data) {
          ElMessage.error(error.response.data.msg || '请求失败，请检查网络')
        } else {
          ElMessage.error('服务器连接异常')
        }
      } finally {
        loading.value = false
      }
    }
  })
}

const handleRegister = () => {
  registerFormRef.value.validate(async (valid) => {
    if (valid) {
      registerLoading.value = true
      try {
        const res = await axios.post('/api/auth/register', registerForm)
        if (res.data.code === 200) {
          ElMessage.success('注册成功，请直接登录')
          registerDialogVisible.value = false
          loginForm.username = registerForm.username
          loginForm.password = registerForm.password
        } else {
          ElMessage.error(res.data.msg || '注册失败')
        }
      } catch (error) {
        if(error.response && error.response.data) {
          ElMessage.error(error.response.data.msg || '请求失败，请检查网络')
        } else {
          ElMessage.error('服务器连接异常')
        }
      } finally {
        registerLoading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-image: url('/Background.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.login-card {
  width: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.card-header {
  text-align: center;
}
.card-header h2 {
  margin: 0;
  font-size: 22px;
  color: #303133;
}
.card-header p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #909399;
}

.login-btn {
  width: 100%;
  margin-top: 10px;
  height: 40px;
  font-size: 16px;
}

.register-btn {
  width: 100%;
  margin-top: 10px;
  margin-left: 0 !important;
  height: 40px;
  font-size: 16px;
}

.hint {
  text-align: center;
  margin-top: 20px;
  font-size: 13px;
  color: #909399;
}
</style>
