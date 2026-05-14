<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './stores/user'

const userStore = useUserStore()

onMounted(() => {
  // 恢复登录状态
  userStore.restoreSession()
})
</script>

<style>
/* 全局样式 */
:root {
  --primary: #3B82F6;
  --primary-light: #EFF6FF;
  --success: #10B981;
  --danger: #EF4444;
  --warning: #F59E0B;
  --gray-50: #F9FAFB;
  --gray-100: #F3F4F6;
  --gray-200: #E5E7EB;
  --gray-300: #D1D5DB;
  --gray-400: #9CA3AF;
  --gray-500: #6B7280;
  --gray-600: #4B5563;
  --gray-700: #374151;
  --gray-800: #1F2937;
  --white: #FFFFFF;
}

body {
  background: var(--gray-50);
  color: var(--gray-800);
}

.page-container {
  min-height: 100vh;
  padding-bottom: 70px; /* 底部导航高度 */
}
</style>
