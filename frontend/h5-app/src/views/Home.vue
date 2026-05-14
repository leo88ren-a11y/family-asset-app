<template>
  <div class="home-page">
    <!-- 顶部问候 + 总资产 -->
    <div class="home-header" @click="$router.push('/detail')">
      <div class="greeting">{{ greeting }}，{{ userStore.userInfo?.nickname || '用户' }} 👋</div>
      <div class="total-label">家庭总资产 (CNY)</div>
      <div class="total-value">
        <span class="currency">¥</span>{{ formatNumber(summary.total_cny) }}
      </div>
      <div v-if="summary.total_cny > 0" class="change-info">
        <span :class="['change-tag', dailyChange >= 0 ? 'up' : 'down']">
          {{ dailyChange >= 0 ? '▲' : '▼' }}
          今日 {{ formatChange(dailyChange) }} ({{ (dailyRate).toFixed(2) }}%)
        </span>
      </div>
    </div>

    <!-- 饼图 + 图例 -->
    <div class="chart-section" @click="$router.push('/detail')" v-if="summary.categories.length > 0">
      <canvas ref="chartCanvas" width="340" height="220"></canvas>
      <div class="legend-list">
        <div
          v-for="cat in summary.categories"
          :key="cat.category"
          class="legend-item"
        >
          <span class="legend-dot" :style="{ background: cat.color }"></span>
          <span class="legend-name">{{ cat.name }}</span>
          <span class="legend-pct">{{ cat.percentage }}%</span>
          <span :class="['legend-change', getCatChange(cat) >= 0 ? 'up' : 'down']">
            {{ getCatChange(cat) >= 0 ? '+' : '' }}{{ getCatChange(cat).toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <van-empty
      v-else
      description="暂无资产数据，点击下方 + 录入第一笔"
      image="search"
    />

    <!-- 分类卡片列表 -->
    <div class="category-cards" v-if="summary.categories.length > 0">
      <div
        v-for="cat in summary.categories"
        :key="cat.category"
        class="category-card"
        @click="$router.push('/detail')"
      >
        <div class="card-header">
          <div class="card-left">
            <span class="cat-icon" :style="{ background: getCategoryBg(cat.category) }">
              {{ getCategoryIcon(cat.category) }}
            </span>
            <span class="cat-name">{{ cat.name }}</span>
          </div>
          <span class="cat-amount">¥{{ formatNumber(cat.amount) }}</span>
        </div>
        <div class="card-body">
          <div class="pct-bar"><div class="pct-fill" :style="{ width: cat.percentage + '%', background: cat.color }"></div></div>
          <span class="pct-text">{{ cat.percentage }}%</span>
        </div>
      </div>
    </div>

    <!-- 底部间距 -->
    <div style="height:24px;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { showToast } from 'vant'
import { assetApi } from '../api'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()
const chartCanvas = ref(null)
const summary = ref({ total_cny: 0, total_count: 0, categories: [] })
const loading = ref(false)

// 模拟日涨跌（后续对接真实行情）
const dailyChange = computed(() => {
  if (!summary.value.total_cny) return 0
  // 随机波动 ±0.5%
  return Math.round(summary.value.total_cny * (Math.random() - 0.5) * 0.01 * 100) / 100
})
const dailyRate = computed(() => {
  if (!summary.value.total_cny) return 0
  return (dailyChange.value / summary.value.total_cny) * 100
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

onMounted(async () => {
  await loadSummary()
})

async function loadSummary() {
  loading.value = true
  try {
    const res = await assetApi.getSummary()
    summary.value = res
    await nextTick()
    drawChart()
  } catch (e) {
    console.error('加载失败', e)
  } finally {
    loading.value = false
  }
}

function drawChart() {
  const canvas = chartCanvas.value
  if (!canvas || !summary.value.categories.length) return
  
  const ctx = canvas.getContext('2d')
  const dpr = window.devicePixelRatio || 1
  const displayWidth = 340
  const displayHeight = 220
  
  canvas.width = displayWidth * dpr
  canvas.height = displayHeight * dpr
  canvas.style.width = displayWidth + 'px'
  canvas.style.height = displayHeight + 'px'
  ctx.scale(dpr, dpr)
  
  ctx.clearRect(0, 0, displayWidth, displayHeight)
  
  const cx = 100, cy = 110, r = 80
  const data = summary.value.categories.filter(c => c.amount > 0)
  
  let startAngle = -Math.PI / 2
  
  data.forEach((cat, i) => {
    const sliceAngle = (cat.percentage / 100) * Math.PI * 2
    
    ctx.beginPath()
    ctx.moveTo(cx, cy)
    ctx.arc(cx, cy, r, startAngle, startAngle + sliceAngle)
    ctx.closePath()
    ctx.fillStyle = cat.color
    ctx.fill()
    
    startAngle += sliceAngle
  })
  
  // 中心白圆（环形图）
  ctx.beginPath()
  ctx.arc(cx, cy, 48, 0, Math.PI * 2)
  ctx.fillStyle = '#FFFFFF'
  ctx.fill()
  
  // 中心文字
  ctx.fillStyle = '#6B7280'
  ctx.font = '13px -apple-system'
  ctx.textAlign = 'center'
  ctx.fillText('配置分布', cx, cy - 6)
  ctx.fillStyle = '#1F2937'
  ctx.font = 'bold 18px -apple-system'
  ctx.fillText(`${data.length}大类`, cx, cy + 16)
}

function formatNumber(num) {
  if (!num) return '0'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function formatChange(val) {
  if (!val) return '¥0'
  return `¥${Math.abs(val).toLocaleString()}`
}

function getCategoryIcon(category) {
  const icons = { equity: '📈', bond: '📊', commodity: '🥇', cash: '💰', other: '📦' }
  return icons[category] || '📦'
}

function getCategoryBg(category) {
  const bgs = {
    equity: '#EFF6FF', bond: '#F5F3FF',
    commodity: '#FFFBEB', cash: '#ECFDF5', other: '#F1F5F9',
  }
  return bgs[category] || '#F1F5F9'
}

function getCatChange(cat) {
  // 模拟分类涨跌
  return (Math.random() - 0.48) * 2
}
</script>

<style scoped>
.home-page {
  padding: 0;
}

.home-header {
  background: white;
  padding: 20px 20px 8px;
  cursor: pointer;
}

.greeting {
  font-size: 15px;
  color: var(--gray-500);
  margin-bottom: 4px;
}

.total-label {
  font-size: 14px;
  color: var(--gray-400);
  margin-bottom: 4px;
}

.total-value {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1.2;
}

.currency {
  font-size: 22px;
  font-weight: 600;
  margin-right: 2px;
}

.change-info {
  margin-top: 8px;
}

.change-tag {
  font-size: 13px;
  font-weight: 500;
}
.change-tag.up { color: #EF4444; }
.change-tag.down { color: #10B981; }

.chart-section {
  background: white;
  margin: 10px 16px;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  gap: 16px;
  align-items: center;
  cursor: pointer;
}

.chart-section canvas {
  flex-shrink: 0;
}

.legend-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}

.legend-name {
  color: var(--gray-700);
  min-width: 56px;
}

.legend-pct {
  font-weight: 600;
  color: var(--gray-800);
  min-width: 36px;
  text-align: right;
}

.legend-change {
  margin-left: auto;
  font-size: 12px;
  font-weight: 500;
}
.legend-change.up { color: #EF4444; }
.legend-change.down { color: #10B981; }

.category-cards {
  padding: 0 16px;
}

.category-card {
  background: white;
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 10px;
  cursor: pointer;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cat-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
}

.cat-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-800);
}

.cat-amount {
  font-size: 16px;
  font-weight: 700;
  color: var(--gray-800);
}

.card-body {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pct-bar {
  flex: 1;
  height: 4px;
  background: var(--gray-100);
  border-radius: 2px;
  overflow: hidden;
}

.pct-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.pct-text {
  font-size: 12px;
  color: var(--gray-400);
  min-width: 32px;
  text-align: right;
}
</style>
