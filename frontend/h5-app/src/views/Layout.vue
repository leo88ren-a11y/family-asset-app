<template>
  <div class="layout">
    <router-view />
    
    <!-- 底部导航 -->
    <van-tabbar
      v-model="activeTab"
      :fixed="true"
      :safe-area-inset-bottom="true"
      :border="false"
      @change="onTabChange"
    >
      <van-tabbar-item name="home" icon="home-o" to="/">总览</van-tabbar-item>
      
      <!-- 中间上传按钮 -->
      <div class="tab-upload-btn" @click="$router.push('/upload')">
        <div class="tab-upload-circle">
          <span>+</span>
        </div>
      </div>
      
      <van-tabbar-item name="profile" icon="user-o" to="/profile">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const activeTab = ref('home')

// 根据路由同步 tab 状态
watch(() => route.path, (path) => {
  if (path === '/' || path.startsWith('/detail')) {
    activeTab.value = 'home'
  } else if (path === '/upload') {
    activeTab.value = 'upload'
  } else if (path === '/profile') {
    activeTab.value = 'profile'
  }
}, { immediate: true })

function onTabChange(name) {
  if (name === 'home') router.push('/')
  else if (name === 'profile') router.push('/profile')
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}

:deep(.van-tabbar) {
  height: 60px;
  background: white;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.06);
}

:deep(.van-tabbar-item) {
  font-size: 11px;
}

.tab-upload-btn {
  position: relative;
  top: -16px;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 56px;
  margin: 0 auto;
}

.tab-upload-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3B82F6, #2563EB);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
  cursor: pointer;
}
</style>
