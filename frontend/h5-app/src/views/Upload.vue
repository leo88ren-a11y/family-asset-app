<template>
  <div class="upload-page">
    <!-- 步骤指示器 -->
    <div class="steps-bar">
      <div v-for="(step, idx) in steps" :key="idx" :class="['step', { active: currentStep === idx, done: currentStep > idx }]">
        <div class="step-dot">
          <van-icon v-if="currentStep > idx" name="passed" size="14" />
          <span v-else>{{ idx + 1 }}</span>
        </div>
        <span class="step-label">{{ step }}</span>
      </div>
    </div>

    <!-- ===== 步骤1：选择截图 ===== -->
    <div v-if="currentStep === 0" class="step-content">
      <div class="upload-area" @click="pickImage">
        <div class="upload-icon">📷</div>
        <p class="upload-title">上传持仓截图</p>
        <p class="upload-sub">支持截图识别，自动提取资产信息</p>
        <p class="upload-formats">支持 JPG、PNG，单张不超过 10MB</p>
      </div>

      <!-- 已选图片预览 -->
      <div v-if="selectedImage" class="image-preview">
        <img :src="previewUrl" alt="预览" @click="showImagePreview = true" />
        <div class="preview-actions">
          <van-button size="small" @click="pickImage">重新选择</van-button>
          <van-button size="small" type="primary" :loading="uploading" @click="uploadImage">
            开始识别
          </van-button>
        </div>
      </div>
    </div>

    <!-- ===== 步骤2：AI 识别中 ===== -->
    <div v-if="currentStep === 1" class="step-content ocr-loading">
      <div class="ocr-animation">
        <div class="ocr-ring"></div>
        <div class="ocr-icon">🔍</div>
      </div>
      <p class="ocr-title">AI 正在识别中...</p>
      <p class="ocr-sub">预计需要 3-5 秒，请稍候</p>
    </div>

    <!-- ===== 步骤3：确认资产信息（多资产列表） ===== -->
    <div v-if="currentStep === 2" class="step-content">
      <div class="ocr-result-banner">
        <van-icon name="info-o" />
        <span>识别到 {{ ocrResult.items.length }} 项资产，请核对后逐一添加</span>
      </div>

      <!-- 已识别的资产列表 -->
      <div v-if="ocrResult.items.length > 0" class="asset-list">
        <div
          v-for="(item, idx) in ocrResult.items"
          :key="idx"
          class="asset-card"
          :class="{ active: confirmedIndices.has(idx), disabled: confirmedIndices.has(idx) }"
        >
          <div class="asset-card-header">
            <span class="asset-card-name">{{ item.name }}</span>
            <span class="asset-card-amount">{{ item.amount?.toLocaleString() }} {{ item.currency }}</span>
          </div>
          <div class="asset-card-detail" v-if="item.code">
            <span>{{ item.code }}</span>
            <span>{{ getCategoryName(item.category) }}</span>
          </div>
          <van-button
            size="small"
            round
            :type="confirmedIndices.has(idx) ? 'default' : 'primary'"
            :disabled="confirmedIndices.has(idx)"
            @click="confirmSingleAsset(item, idx)"
          >
            {{ confirmedIndices.has(idx) ? '已添加' : '确认添加' }}
          </van-button>
        </div>
      </div>

      <!-- 无结果提示 -->
      <div v-else class="no-result">
        <p>未识别到资产信息</p>
        <p class="no-result-sub">可尝试重新上传更清晰的截图</p>
      </div>

      <div class="action-btns">
        <van-button size="large" round plain style="margin-top:12px;" @click="resetUpload">
          重新上传
        </van-button>
      </div>
    </div>

    <!-- 资产分类选择器 -->
    <van-popup v-model:show="showCategoryPicker" position="bottom" round>
      <van-picker
        :columns="categoryColumns"
        @confirm="onCategoryConfirm"
        @cancel="showCategoryPicker = false"
      />
    </van-popup>

    <!-- 图片预览 -->
    <van-image-preview v-model:show="showImagePreview" :images="[previewUrl]" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, showLoadingToast, closeToast } from 'vant'
import { assetApi } from '../api'

const router = useRouter()

const steps = ['选择截图', 'AI 识别', '确认保存'] // v2
const currentStep = ref(0)
const selectedImage = ref(null)
const previewUrl = ref('')
const uploading = ref(false)
const saving = ref(false)
const showImagePreview = ref(false)
const showCategoryPicker = ref(false)

const ocrResult = ref({ success: false, items: [] })
const confirmedIndices = ref(new Set())  // 已确认添加的资产索引


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

function pickImage() {
  // 通过 Android 桥接调用原生相册
  if (window.AndroidBridge && window.AndroidBridge.pickImage) {
    window.AndroidBridge.pickImage()
  } else {
    // H5 降级：file input
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = (e) => {
      const file = e.target.files[0]
      if (file) handleFileSelect(file)
    }
    input.click()
  }
}

// Android 回调：图片选择完成
function onImageSelected(filePath) {
  // 从 filePath 加载文件（通过 fetch blob）
  fetch(filePath)
    .then(r => r.blob())
    .then(blob => {
      const file = new File([blob], 'screenshot.jpg', { type: 'image/jpeg' })
      handleFileSelect(file)
    })
}

window.onImageSelected = onImageSelected

function handleFileSelect(file) {
  selectedImage.value = file
  previewUrl.value = URL.createObjectURL(file)
}

async function uploadImage() {
  if (!selectedImage.value) return
  uploading.value = true
  currentStep.value = 1
  
  try {
    const res = await assetApi.ocrUpload(selectedImage.value)
    ocrResult.value = res
    
    // 显示所有识别结果
    confirmedIndices.value.clear()
    
    currentStep.value = 2
  } catch (e) {
    console.error(e)
    showToast('识别失败，请重试')
    currentStep.value = 0
  } finally {
    uploading.value = false
  }
}

async function confirmSingleAsset(item, idx) {
  saving.value = true
  try {
    await assetApi.ocrConfirm({
      name: item.name,
      code: item.code || '',
      category: item.category || 'equity',
      amount: parseFloat(item.amount),
      currency: item.currency || 'CNY',
      cost: null,
      platform: '',
    })
    
    confirmedIndices.value.add(idx)
    showSuccessToast(`${item.name} 已添加`)
  } catch (e) {
    showToast('保存失败：' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

function resetUpload() {
  currentStep.value = 0
  selectedImage.value = null
  previewUrl.value = ''
  ocrResult.value = { success: false, items: [] }
  confirmedIndices.value.clear()
}
</script>

<style scoped>
.upload-page {
  min-height: 100vh;
  background: var(--gray-50);
  padding-bottom: 40px;
}

/* 步骤条 */
.steps-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px 24px;
  background: white;
  gap: 0;
}

.step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--gray-400);
}

.step.active { color: #3B82F6; font-weight: 600; }
.step.done { color: #10B981; }

.step-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid currentColor;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.step.done .step-dot {
  background: #10B981;
  border-color: #10B981;
  color: white;
}

.step-label {
  font-size: 13px;
}

.step:not(:last-child)::after {
  content: '';
  display: block;
  width: 40px;
  height: 1px;
  background: var(--gray-200);
  margin: 0 8px;
}

/* 步骤内容 */
.step-content {
  padding: 16px;
}

.upload-area {
  background: white;
  border-radius: 16px;
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  border: 2px dashed var(--gray-200);
  transition: border-color 0.2s;
}

.upload-area:active {
  border-color: #3B82F6;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.upload-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--gray-800);
  margin-bottom: 6px;
}

.upload-sub {
  font-size: 14px;
  color: var(--gray-500);
  margin-bottom: 4px;
}

.upload-formats {
  font-size: 12px;
  color: var(--gray-400);
}

.image-preview {
  margin-top: 16px;
  background: white;
  border-radius: 16px;
  overflow: hidden;
}

.image-preview img {
  width: 100%;
  max-height: 300px;
  object-fit: contain;
  background: var(--gray-100);
}

.preview-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 12px;
}

/* OCR 加载动画 */
.ocr-loading {
  padding: 60px 24px;
  text-align: center;
}

.ocr-animation {
  position: relative;
  width: 100px;
  height: 100px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ocr-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid #EFF6FF;
  border-top-color: #3B82F6;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.ocr-icon {
  font-size: 36px;
}

.ocr-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-800);
  margin-bottom: 8px;
}

.ocr-sub {
  font-size: 14px;
  color: var(--gray-400);
}

/* 资产表单 */
.asset-form {
  margin-top: 16px;
}

:deep(.van-cell-group--inset) {
  margin: 0;
  border-radius: 12px;
}

:deep(.van-dropdown-menu) {
  height: 24px;
}

.ocr-result-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #FFF7ED;
  color: #D97706;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 10px;
  margin-bottom: 12px;
}

/* 资产卡片列表 */
.asset-list {
  margin-top: 12px;
}

.asset-card {
  background: white;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  border: 1.5px solid var(--gray-200);
  transition: all 0.2s;
}

.asset-card.active {
  opacity: 0.5;
  background: var(--gray-50);
  border-color: #10B981;
}

.asset-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.asset-card-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-800);
}

.asset-card-amount {
  font-size: 15px;
  font-weight: 700;
  color: #3B82F6;
}

.asset-card-detail {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--gray-400);
  margin-bottom: 10px;
}

.asset-card .van-button {
  min-width: 90px;
}

.no-result {
  text-align: center;
  padding: 40px 0;
  color: var(--gray-400);
}

.no-result-sub {
  font-size: 13px;
  color: var(--gray-300);
  margin-top: 4px;
}

.action-btns {
  padding: 20px 16px 0;
}
</style>
