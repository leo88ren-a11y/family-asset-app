<template>
  <div class="detail-page">
    <!-- 导航栏 -->
    <van-nav-bar
      title="配置详情"
      left-arrow
      @click-left="$router.back()"
      :border="false"
    >
      <template #right>
        <div class="sort-btn" @click="toggleSort">
          <van-icon name="sort" size="16" />
          {{ sortLabel }}
        </div>
      </template>
    </van-nav-bar>

    <!-- 资产列表 -->
    <div class="detail-content" v-if="assets.length > 0">
      <!-- 按分类分组 -->
      <template v-for="(group, catKey) in groupedAssets" :key="catKey">
        <div class="group-header">
          {{ getCategoryName(catKey) }} · {{ getGroupPct(group) }}%
        </div>
        
        <div
          v-for="item in group"
          :key="item.id"
          class="asset-item"
        >
          <div class="asset-main">
            <div class="asset-name-row">
              <span class="asset-name">{{ item.name }}</span>
              <span class="asset-amount">¥{{ formatNumber(item.amount) }}</span>
            </div>
            <div class="asset-sub-row">
              <span class="asset-code" v-if="item.code">{{ item.code }}</span>
              <span class="asset-merge" v-if="item.merge_count && item.merge_count > 1">
                {{ item.merge_count }}账户合并
              </span>
            </div>
          </div>
          <div class="asset-right">
            <div class="asset-pct">{{ item.percentage }}%</div>
            <div :class="['asset-profit', item.profit >= 0 ? 'up' : 'down']" v-if="item.profit !== null">
              {{ item.profit >= 0 ? '+' : '' }}¥{{ formatNumber(item.profit) }}
            </div>
          </div>
        </div>
      </template>

      <!-- 未分组的资产 -->
      <template v-if="ungroupedAssets.length > 0">
        <div class="group-header">其他</div>
        <div v-for="item in ungroupedAssets" :key="item.id" class="asset-item">
          <div class="asset-main">
            <div class="asset-name-row">
              <span class="asset-name">{{ item.name }}</span>
              <span class="asset-amount">¥{{ formatNumber(item.amount) }}</span>
            </div>
            <div class="asset-sub-row">
              <span class="asset-code" v-if="item.code">{{ item.code }}</span>
            </div>
          </div>
          <div class="asset-right">
            <div class="asset-pct">{{ item.percentage }}%</div>
          </div>
        </div>
      </template>
    </div>

    <!-- 空状态 -->
    <van-empty v-else description="暂无资产数据" image="search" />

    <div style="height:24px;"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { showToast, showLoadingToast, closeToast } from 'vant'
import { assetApi } from '../api'

const assets = ref([])
const sortBy = ref('pct')
const totalCny = ref(0)

const sortLabels = {
  pct: '按占比',
  amount: '按金额',
  name: '按名称',
}
const sortLabel = computed(() => sortLabels[sortBy.value])

onMounted(async () => {
  await loadAssets()
})

async function loadAssets() {
  showLoadingToast({ message: '加载中...', forbidClick: true })
  try {
    const res = await assetApi.getList(sortBy.value)
    assets.value = res.items || []
    totalCny.value = res.total_cny || 0
  } catch (e) {
    console.error(e)
  } finally {
    closeToast()
  }
}

function toggleSort() {
  const order = ['pct', 'amount', 'name']
  const idx = order.indexOf(sortBy.value)
  sortBy.value = order[(idx + 1) % order.length]
  loadAssets()
}

// 按分类分组
const groupedAssets = computed(() => {
  const groups = {}
  for (const a of assets.value) {
    if (!groups[a.category]) groups[a.category] = []
    groups[a.category].push(a)
  }
  return groups
})

// 没有分类的资产（理论上不应该有）
const ungroupedAssets = computed(() => [])

function getGroupPct(group) {
  if (!totalCny.value) return 0
  const sum = group.reduce((s, a) => s + (a.amount || 0), 0)
  return Math.round(sum / totalCny.value * 100 * 10) / 10
}

function getCategoryName(cat) {
  const names = {
    equity: '权益类',
    bond: '债券类',
    commodity: '大宗商品',
    cash: '现金类',
    other: '其他',
  }
  return names[cat] || cat
}

function formatNumber(num) {
  if (!num) return '0'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}
</script>

<style scoped>
.detail-page {
  background: var(--gray-50);
  min-height: 100vh;
}

:deep(.van-nav-bar) {
  background: white;
}

.sort-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--gray-500);
  padding: 4px 10px;
  border-radius: 8px;
  border: 1px solid var(--gray-200);
  cursor: pointer;
}

.detail-content {
  padding: 8px 16px;
}

.group-header {
  font-size: 13px;
  color: var(--gray-400);
  padding: 14px 4px 6px;
}

.asset-item {
  background: white;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.asset-main {
  flex: 1;
  min-width: 0;
}

.asset-name-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}

.asset-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-800);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-amount {
  font-size: 16px;
  font-weight: 700;
  color: var(--gray-800);
  flex-shrink: 0;
}

.asset-sub-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.asset-code {
  font-size: 12px;
  color: var(--gray-400);
}

.asset-merge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #EFF6FF;
  color: #3B82F6;
}

.asset-right {
  text-align: right;
  flex-shrink: 0;
  margin-left: 12px;
}

.asset-pct {
  font-size: 13px;
  color: var(--gray-500);
  margin-bottom: 2px;
}

.asset-profit {
  font-size: 12px;
  font-weight: 500;
}
.asset-profit.up { color: #EF4444; }
.asset-profit.down { color: #10B981; }
</style>
