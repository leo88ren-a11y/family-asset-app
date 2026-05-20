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

    <!-- ===== 步骤3：确认并编辑资产信息 ===== -->
    <div v-if="currentStep === 2" class="step-content">
      <!-- 结果提示 -->
      <div class="ocr-result-banner" :class="{ 'banner-warn': editableItems.length === 0 }">
        <van-icon name="info-o" />
        <span v-if="editableItems.length > 0">识别到 {{ editableItems.length }} 项资产，请核对并编辑后保存</span>
        <span v-else>未识别到资产信息，可尝试重新上传更清晰的截图</span>
      </div>

      <!-- 可编辑资产列表 -->
      <div v-if="editableItems.length > 0" class="asset-edit-list">
        <div
          v-for="(item, idx) in editableItems"
          :key="idx"
          class="asset-edit-card"
          :class="{ saved: item.saved }"
        >
          <!-- 卡片头部：资产序号 + 名称 + 删除按钮 -->
          <div class="edit-card-header">
            <span class="edit-card-index">资产 {{ idx + 1 }}</span>
            <van-icon
              v-if="!item.saved"
              name="delete-o"
              color="#999"
              size="18"
              @click="removeAsset(idx)"
            />
            <van-icon v-else name="passed" color="#10B981" size="18" />
          </div>

          <!-- 可编辑字段 -->
          <van-cell-group inset>
            <!-- 资产名称 -->
            <van-field
              v-model="item.name"
              label="名称"
              placeholder="如：中证500ETF"
              :border="false"
              input-align="right"
            />
            <!-- 代码 -->
            <van-field
              v-model="item.code"
              label="代码"
              placeholder="如：510500.SH"
              :border="false"
              input-align="right"
            />
            <!-- 分类 -->
            <van-field
              v-model="item.categoryLabel"
              is-link
              readonly
              label="分类"
              placeholder="选择分类"
              :border="false"
              @click="openCategoryPicker(idx)"
            />
            <!-- 金额 -->
            <van-field
              v-model="item.amountStr"
              label="金额"
              type="text"
              inputmode="decimal"
              placeholder="输入金额"
              :formatter="formatAmount"
              :border="false"
              input-align="right"
              @blur="onAmountBlur(item)"
            >
              <template #button>
                <span class="currency-tag">{{ item.currency }}</span>
              </template>
            </van-field>
            <!-- 成本（可选） -->
            <van-field
              v-model="item.costStr"
              label="成本（选填）"
              type="text"
              inputmode="decimal"
              placeholder="输入成本价"
              :formatter="formatAmount"
              :border="false"
              input-align="right"
              @blur="onCostBlur(item)"
            >
              <template #button>
                <span class="currency-tag">{{ item.currency }}</span>
              </template>
            </van-field>
          </van-cell-group>

          <!-- 已保存标识 -->
          <div v-if="item.saved" class="edit-card-action">
            <div class="saved-badge">
              <van-icon name="passed" /> 已保存
            </div>
          </div>
        </div>
      </div>

      <!-- 全部保存按钮 -->
      <div v-if="editableItems.length > 0" class="action-btns">
        <van-button
          size="large"
          round
          type="primary"
          :loading="savingAll"
          :disabled="allSaved || savingAll"
          @click="saveAllAssets"
        >
          {{ allSaved ? '全部已保存' : '全部保存' }}
        </van-button>
        <van-button size="large" round plain @click="resetUpload" style="margin-top: 10px;">
          重新上传
        </van-button>
      </div>
      <div v-else class="action-btns">
        <van-button size="large" round plain @click="resetUpload">
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
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, closeToast } from 'vant'
import { assetApi } from '../api'

const router = useRouter()

const steps = ['选择截图', 'AI 识别', '确认保存']
const currentStep = ref(0)
const selectedImage = ref(null)
const previewUrl = ref('')
const uploading = ref(false)
const showImagePreview = ref(false)
const showCategoryPicker = ref(false)
const currentEditIndex = ref(-1) // 当前正在编辑分类的资产索引

// 分类选项
const categoryColumns = [
  { text: '权益类', value: 'equity' },
  { text: '债券类', value: 'bond' },
  { text: '大宗商品', value: 'commodity' },
  { text: '现金类', value: 'cash' },
  { text: '其他', value: 'other' },
]

// 可编辑资产列表（每项都是响应式对象）
const editableItems = ref([])
const savingAll = ref(false)

// 是否全部已保存
const allSaved = computed(() =>
  editableItems.value.length > 0 && editableItems.value.every(item => item.saved)
)

function getCategoryLabel(cat) {
  const map = {
    equity: '权益类',
    bond: '债券类',
    commodity: '大宗商品',
    cash: '现金类',
    other: '其他',
  }
  return map[cat] || cat || '权益类'
}

function pickImage() {
  if (window.AndroidBridge && window.AndroidBridge.pickImage) {
    window.AndroidBridge.pickImage()
  } else {
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

// Android 回调
function onImageSelected(filePath) {
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

    // 将 OCR 结果转为可编辑表单数据
    const items = (res.items || []).map(item => ({
      name: item.name || '',
      code: item.code || '',
      category: item.category || 'equity',
      categoryLabel: getCategoryLabel(item.category),
      amount: parseFloat(item.amount) || 0,
      amountStr: toFixed2(parseFloat(item.amount) || 0),
      cost: item.cost ? parseFloat(item.cost) : null,
      costStr: item.cost ? toFixed2(parseFloat(item.cost)) : '',
      currency: item.currency || 'CNY',
      platform: item.platform || '',
      saved: false,
      saving: false,
    }))

    editableItems.value = items
    currentStep.value = 2
  } catch (e) {
    console.error(e)
    showToast('识别失败，请重试')
    currentStep.value = 0
  } finally {
    uploading.value = false
  }
}

function openCategoryPicker(idx) {
  currentEditIndex.value = idx
  showCategoryPicker.value = true
}

function onCategoryConfirm({ selectedOptions }) {
  if (currentEditIndex.value >= 0 && currentEditIndex.value < editableItems.value.length) {
    const item = editableItems.value[currentEditIndex.value]
    item.category = selectedOptions[0]?.value || 'equity'
    item.categoryLabel = selectedOptions[0]?.text || '权益类'
  }
  showCategoryPicker.value = false
  currentEditIndex.value = -1
}

// -------- 金额格式化 --------
function toFixed2(val) {
  if (val === null || val === undefined || val === '') return ''
  const n = parseFloat(val)
  if (isNaN(n)) return ''
  return n.toFixed(2)
}

// Vant formatter：只允许合法小数格式
function formatAmount(value) {
  // 允许：空、整数、小数（最多两位）
  return value.replace(/[^0-9.]/g, '').replace(/(\..*)\./g, '$1').replace(/^(\d*\.\d{0,2}).*/g, '$1')
}

// 失焦时确保两位小数显示
function onAmountBlur(item) {
  item.amountStr = toFixed2(item.amountStr)
}

function onCostBlur(item) {
  item.costStr = toFixed2(item.costStr)
}

// -------- 全部保存 --------
async function saveAllAssets() {
  // 检查是否有未填名称的
  const emptyNames = editableItems.value.filter(item => !item.name.trim())
  if (emptyNames.length > 0) {
    showToast('请填写所有资产的名称后再保存')
    return
  }

  savingAll.value = true
  try {
    await Promise.all(
      editableItems.value
        .filter(item => !item.saved)
        .map(item =>
          assetApi.create({
            name: item.name.trim(),
            code: item.code.trim(),
            category: item.category,
            amount: parseFloat(item.amountStr) || 0,
            currency: item.currency,
            cost: item.costStr ? parseFloat(item.costStr) : null,
            platform: item.platform,
          }).then(() => { item.saved = true })
          .catch(e => { throw new Error(`${item.name} 保存失败`) })
        )
    )
    showSuccessToast(`已保存 ${editableItems.value.length} 项资产`)
  } catch (e) {
    showToast(e.message || '保存失败，请重试')
  } finally {
    savingAll.value = false
  }
}

function removeAsset(idx) {
  editableItems.value.splice(idx, 1)
}

function resetUpload() {
  currentStep.value = 0
  selectedImage.value = null
  previewUrl.value = ''
  editableItems.value = []
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

.step-label { font-size: 13px; }
.step:not(:last-child)::after {
  content: '';
  display: block;
  width: 40px;
  height: 1px;
  background: var(--gray-200);
  margin: 0 8px;
}

.step-content { padding: 16px; }

/* 上传区域 */
.upload-area {
  background: white;
  border-radius: 16px;
  padding: 40px 24px;
  text-align: center;
  cursor: pointer;
  border: 2px dashed var(--gray-200);
  transition: border-color 0.2s;
}
.upload-area:active { border-color: #3B82F6; }

.upload-icon { font-size: 48px; margin-bottom: 12px; }
.upload-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--gray-800);
  margin-bottom: 6px;
}
.upload-sub { font-size: 14px; color: var(--gray-500); margin-bottom: 4px; }
.upload-formats { font-size: 12px; color: var(--gray-400); }

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

/* OCR 加载 */
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
@keyframes spin { to { transform: rotate(360deg); } }
.ocr-icon { font-size: 36px; }
.ocr-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-800);
  margin-bottom: 8px;
}
.ocr-sub { font-size: 14px; color: var(--gray-400); }

/* 结果提示 */
.ocr-result-banner {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #EFF6FF;
  color: #3B82F6;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 10px;
  margin-bottom: 14px;
}
.ocr-result-banner.banner-warn {
  background: #FFF7ED;
  color: #D97706;
}

/* 可编辑资产卡片 */
.asset-edit-list { margin-top: 8px; }

.asset-edit-card {
  background: white;
  border-radius: 14px;
  margin-bottom: 14px;
  overflow: hidden;
  border: 1.5px solid var(--gray-200);
  transition: all 0.25s;
}
.asset-edit-card.saved {
  border-color: #10B981;
  background: #F0FDF4;
}

.edit-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px 4px;
}
.edit-card-index {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-700);
}

.edit-card-header .van-icon {
  cursor: pointer;
  padding: 4px;
}

:deep(.van-cell-group--inset) {
  margin: 0 12px;
  border-radius: 10px;
}

:deep(.van-field__label) {
  color: var(--gray-600);
  width: 80px;
}

.currency-tag {
  font-size: 13px;
  color: var(--gray-400);
  background: var(--gray-100);
  padding: 2px 8px;
  border-radius: 4px;
}

.edit-card-action {
  padding: 10px 16px 14px;
}

.saved-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 13px;
  color: #10B981;
  font-weight: 500;
  padding: 6px 0;
}

.action-btns {
  padding: 20px 16px 0;
}
</style>
