<!-- 整体页面布局。包含左侧导航栏（Logo + 菜单项 + 高亮指示条）和右侧内容区，菜单项动态高亮当前路由 -->

<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <span v-show="!isCollapse">谣言分析系统</span>
        <span v-show="isCollapse">谣言</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        :collapse="isCollapse"
        background-color="#ffffff"
        text-color="#475569"
        active-text-color="#2563eb"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>系统概览</template>
        </el-menu-item>
        
        <el-menu-item index="/topics">
          <el-icon><PieChart /></el-icon>
          <template #title>热点主题分析</template>
        </el-menu-item>

        <el-menu-item index="/trends">
          <el-icon><TrendCharts /></el-icon>
          <template #title>传播趋势分析</template>
        </el-menu-item>

        <el-menu-item index="/rumors">
          <el-icon><Search /></el-icon>
          <template #title>谣言库检索</template>
        </el-menu-item>

        <el-menu-item v-if="userRole === 'admin'" index="/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="main-container">
      <el-header class="header">
        <div class="left">
          <el-icon class="toggle-icon" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/" class="breadcrumb">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              欢迎, {{ userName }} ({{ userRoleLabel }})
              <el-icon class="el-icon--right"><CaretBottom /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  DataBoard, PieChart, TrendCharts, Search, User,
  Fold, Expand, CaretBottom
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const isCollapse = ref(false)

const userName = ref(sessionStorage.getItem('name') || 'User')
const userRole = ref(sessionStorage.getItem('role') || 'analyst')

const userRoleLabel = computed(() => {
  return userRole.value === 'admin' ? '系统管理员' : '数据分析员'
})

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '系统概览')

const handleCommand = (command) => {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }).then(() => {
      sessionStorage.clear()
      router.push('/login')
      ElMessage.success('已退出登录')
    }).catch(() => {})
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
  width: 100%;
}

/* 侧边栏 */
.aside {
  background-color: #ffffff;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow-x: hidden;
  box-shadow: 2px 0 20px rgba(0,0,0,0.04);
  z-index: 10;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #f1f5f9;
}

/* Logo区 */
.logo {
  height: 70px;
  line-height: 70px;
  text-align: center;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 1.5px;
  background-color: #ffffff;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  /* 文字渐变高光核心代码 */
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  padding: 0 10px;
}

.el-menu-vertical {
  border-right: none;
  padding: 16px 12px;
  flex: 1;
}

/* 菜单项 */
:deep(.el-menu-item) {
  height: 52px;
  line-height: 52px;
  margin-bottom: 6px;
  border-radius: 10px;
  color: #64748b !important;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
  padding-left: 20px !important;
  position: relative;
  overflow: hidden;
}

/* Hover状态：高级灰底 */
:deep(.el-menu-item:hover) {
  background-color: #f8fafc !important; 
  color: #0f172a !important;
  transform: translateX(4px);
}

/* Active状态：左侧粗线条指示器 + 浅柔色底层 + 品牌色亮字 */
.el-menu-vertical:not(.el-menu--collapse) :deep(.el-menu-item.is-active) {
  background-color: #eff6ff !important;
  color: #2563eb !important;
  font-weight: 700;
  transform: translateX(0);
}

/* 最左侧线条 */
.el-menu-vertical:not(.el-menu--collapse) :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 5px;
  background: linear-gradient(to bottom, #3b82f6, #6366f1);
  border-radius: 0 4px 4px 0;
}

:deep(.el-menu--collapse .el-menu-item.is-active) {
  background-color: #eff6ff !important;
  color: #2563eb !important;
  border-radius: 10px;
}

:deep(.el-menu-item [class^="el-icon"]) {
  font-size: 20px;
  margin-right: 14px;
  transition: color 0.3s;
}

:deep(.el-menu-item.is-active [class^="el-icon"]) {
  color: #2563eb;
}

.header {
  background-color: #ffffff;
  color: #333;
  line-height: 60px;
  display: flex;
  justify-content: space-between;
  box-shadow: 0 1px 10px rgba(0,0,0,0.03);
  padding: 0 24px;
  z-index: 5;
}

.header .left {
  display: flex;
  align-items: center;
}

.toggle-icon {
  font-size: 22px;
  cursor: pointer;
  margin-right: 24px;
  color: #64748b;
  transition: color 0.2s;
}

.toggle-icon:hover {
  color: #2563eb;
}

.breadcrumb {
  line-height: 60px;
}

.header .right {
  display: flex;
  align-items: center;
}

.user-info {
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  color: #475569;
  display: flex;
  align-items: center;
}

.main-content {
  background-color: #f1f5f9;
  padding: 24px;
}

/* 页面切换动画 */
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.3s;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
