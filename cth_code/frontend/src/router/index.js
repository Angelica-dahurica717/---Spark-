// 路由配置。定义所有页面的 URL 路径映射，实现路由守卫：未登录自动跳转到登录页，已登录不能回到登录页

import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/',
    component: () => import('@/layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '系统概览' }
      },
      {
        path: 'topics',
        name: 'TopicAnalysis',
        component: () => import('@/views/TopicAnalysis.vue'),
        meta: { title: '热点主题分析' }
      },
      {
        path: 'trends',
        name: 'TemporalTrend',
        component: () => import('@/views/TemporalTrend.vue'),
        meta: { title: '传播趋势分析' }
      },
      {
        path: 'rumors',
        name: 'RumorSearch',
        component: () => import('@/views/RumorSearch.vue'),
        meta: { title: '谣言库检索' }
      },
      {
        path: 'users',
        name: 'UserManage',
        component: () => import('@/views/UserManage.vue'),
        meta: { title: '用户管理', roles: ['admin'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：校验 token
router.beforeEach((to, from, next) => {
  const token = sessionStorage.getItem('token')
  const role = sessionStorage.getItem('role')
  
  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.meta.roles && !to.meta.roles.includes(role)) {
    next('/dashboard') // 权限不足跳转主页
  } else {
    next()
  }
})

export default router
