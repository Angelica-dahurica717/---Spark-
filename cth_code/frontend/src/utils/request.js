// Axios 请求封装。统一给所有请求自动加上 JWT Token 请求头，统一处理 401 未授权响应（自动跳转登录页）

import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: '', // vite proxy -> /api
  timeout: 10000
})

request.interceptors.request.use(
  config => {
    const token = sessionStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = 'Bearer ' + token
    }
    return config
  },
  error => Promise.reject(error)
)

request.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code === 401) {
      ElMessage.error(res.msg || '未登录或Token过期')
      sessionStorage.clear()
      router.push('/login')
      return Promise.reject(new Error(res.msg || 'Error'))
    }
    return res
  },
  error => {
    if (error.response?.status === 401 || error.response?.data?.code === 401) {
      sessionStorage.clear()
      router.push('/login')
    }
    ElMessage.error(error.message || '网络请求错误')
    return Promise.reject(error)
  }
)

export default request
