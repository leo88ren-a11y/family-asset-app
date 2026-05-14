<template>
  <div class="profile-page">
    <!-- 用户信息卡 -->
    <div class="user-card">
      <div class="user-avatar">{{ avatarText }}</div>
      <div class="user-info">
        <div class="user-nickname" @click="showNicknameEditor = true">
          {{ userStore.userInfo?.nickname || '用户' }}
          <van-icon name="edit" size="13" />
        </div>
        <div class="user-phone">{{ formatPhone(userStore.userInfo?.phone) }}</div>
      </div>
    </div>

    <!-- 家庭信息 -->
    <div class="section">
      <div class="section-title">家庭管理</div>
      <div class="family-card">
        <template v-if="familyInfo">
          <div class="family-header">
            <span class="family-name">🏠 {{ familyInfo.name }}</span>
            <span class="member-count">{{ members.length }} 人</span>
          </div>
          <div class="member-list">
            <div v-for="m in members" :key="m.id" class="member-item">
              <div class="member-avatar-sm">{{ m.nickname[0] }}</div>
              <span>{{ m.nickname }}</span>
              <span v-if="m.id === userStore.userInfo?.id" class="member-tag">我</span>
            </div>
          </div>
          <div class="invite-code-row">
            <span class="invite-label">邀请码</span>
            <span class="invite-code">{{ familyInfo.invite_code }}</span>
            <van-button size="small" @click="copyInviteCode">复制</van-button>
          </div>
        </template>
        <template v-else>
          <div class="family-empty">
            <p>您还没有加入任何家庭</p>
            <div class="family-actions">
              <van-button size="small" type="primary" @click="showCreateFamily = true">创建家庭</van-button>
              <van-button size="small" @click="showJoinFamily = true">加入家庭</van-button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- 资产管理 -->
    <div class="section">
      <div class="section-title">资产分类说明</div>
      <div class="category-guide">
        <div v-for="cat in categoryGuide" :key="cat.key" class="guide-item">
          <span class="guide-icon">{{ cat.icon }}</span>
          <div class="guide-content">
            <span class="guide-name">{{ cat.name }}</span>
            <span class="guide-desc">{{ cat.desc }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 关于 -->
    <div class="section">
      <div class="section-title">关于</div>
      <van-cell-group inset>
        <van-cell title="版本" value="v1.0.0" />
        <van-cell title="隐私政策" is-link @click="showPrivacy = true" />
        <van-cell title="用户协议" is-link @click="showTerms = true" />
      </van-cell-group>
    </div>

    <!-- 退出登录 -->
    <div class="logout-btn-wrap">
      <van-button block round plain type="default" @click="handleLogout">
        退出登录
      </van-button>
    </div>

    <!-- 修改昵称弹窗 -->
    <van-dialog
      v-model:show="showNicknameEditor"
      title="修改昵称"
      show-cancel-button
      @confirm="updateNickname"
    >
      <div style="padding: 16px;">
        <van-field v-model="nicknameInput" placeholder="请输入昵称" />
      </div>
    </van-dialog>

    <!-- 创建家庭弹窗 -->
    <van-dialog
      v-model:show="showCreateFamily"
      title="创建家庭"
      show-cancel-button
      @confirm="createFamily"
    >
      <div style="padding: 16px;">
        <van-field v-model="familyNameInput" label="家庭名称" placeholder="如：老王家" />
      </div>
    </van-dialog>

    <!-- 加入家庭弹窗 -->
    <van-dialog
      v-model:show="showJoinFamily"
      title="加入家庭"
      show-cancel-button
      @confirm="joinFamily"
    >
      <div style="padding: 16px;">
        <van-field v-model="joinCodeInput" label="邀请码" placeholder="请输入8位邀请码" />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, showLoadingToast, closeToast } from 'vant'
import { authApi, familyApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const familyInfo = ref(null)
const members = ref([])
const showNicknameEditor = ref(false)
const showCreateFamily = ref(false)
const showJoinFamily = ref(false)
const showPrivacy = ref(false)
const showTerms = ref(false)
const nicknameInput = ref('')
const familyNameInput = ref('')
const joinCodeInput = ref('')

const avatarText = computed(() => {
  const name = userStore.userInfo?.nickname || '用'
  return name.slice(0, 1)
})

const categoryGuide = [
  { key: 'equity', name: '权益类', icon: '📈', desc: '股票、公募基金、私募基金、REITs' },
  { key: 'bond', name: '债券类', icon: '📊', desc: '国债、企业债、可转债、债券基金' },
  { key: 'commodity', name: '大宗商品', icon: '🥇', desc: '黄金ETF、黄金存单、原油' },
  { key: 'cash', name: '现金类', icon: '💰', desc: '银行存款、货币基金、大额存单' },
  { key: 'other', name: '其他', icon: '📦', desc: '古董、艺术品、加密货币等' },
]

onMounted(async () => {
  await loadFamilyInfo()
})

async function loadFamilyInfo() {
  if (!userStore.userInfo?.family_id) return
  try {
    const [familyRes, memberRes] = await Promise.all([
      familyApi.getDetail(),
      familyApi.getMembers(),
    ])
    familyInfo.value = familyRes
    members.value = memberRes
  } catch (e) {
    console.error(e)
  }
}

function updateNickname() {
  if (!nicknameInput.value.trim()) return
  authApi.updateNickname({ nickname: nicknameInput.value }).then(() => {
    userStore.userInfo.nickname = nicknameInput.value
    showSuccessToast('昵称已更新')
  })
}

function createFamily() {
  if (!familyNameInput.value.trim()) {
    showToast('请输入家庭名称')
    return
  }
  showLoadingToast({ message: '创建中...', forbidClick: true })
  authApi.createFamily(familyNameInput.value).then(() => {
    closeToast()
    showSuccessToast('家庭创建成功')
    userStore.userInfo.family_id = 1 // 触发刷新
    loadFamilyInfo()
  }).catch(() => closeToast())
}

function joinFamily() {
  if (!joinCodeInput.value.trim()) {
    showToast('请输入邀请码')
    return
  }
  showLoadingToast({ message: '加入中...', forbidClick: true })
  authApi.joinFamily(joinCodeInput.value).then(() => {
    closeToast()
    showSuccessToast('加入成功')
    userStore.userInfo.family_id = 1
    loadFamilyInfo()
  }).catch(() => closeToast())
}

function copyInviteCode() {
  if (!familyInfo.value?.invite_code) return
  navigator.clipboard.writeText(familyInfo.value.invite_code)
  showSuccessToast('邀请码已复制')
}

function formatPhone(phone) {
  if (!phone) return ''
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

function handleLogout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: var(--gray-50);
  padding-bottom: 40px;
}

.user-card {
  background: linear-gradient(135deg, #3B82F6, #60A5FA);
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  color: white;
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255,255,255,0.4);
}

.user-nickname {
  font-size: 19px;
  font-weight: 600;
  color: white;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.user-phone {
  font-size: 13px;
  color: rgba(255,255,255,0.75);
  margin-top: 4px;
}

.section {
  margin-top: 16px;
  padding: 0 16px;
}

.section-title {
  font-size: 13px;
  color: var(--gray-400);
  padding: 0 4px 8px;
}

.family-card {
  background: white;
  border-radius: 14px;
  padding: 16px;
}

.family-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.family-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-800);
}

.member-count {
  font-size: 12px;
  color: var(--gray-400);
  background: var(--gray-100);
  padding: 2px 8px;
  border-radius: 8px;
}

.member-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--gray-600);
}

.member-avatar-sm {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #EFF6FF;
  color: #3B82F6;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.member-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #DBEAFE;
  color: #3B82F6;
}

.invite-code-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--gray-100);
}

.invite-label {
  font-size: 13px;
  color: var(--gray-400);
}

.invite-code {
  font-size: 14px;
  font-family: monospace;
  font-weight: 600;
  color: var(--gray-800);
  flex: 1;
  letter-spacing: 2px;
}

.family-empty {
  text-align: center;
  padding: 8px 0;
}

.family-empty p {
  font-size: 14px;
  color: var(--gray-500);
  margin-bottom: 16px;
}

.family-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.category-guide {
  background: white;
  border-radius: 14px;
  overflow: hidden;
}

.guide-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--gray-100);
}

.guide-item:last-child {
  border-bottom: none;
}

.guide-icon {
  font-size: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.guide-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.guide-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
}

.guide-desc {
  font-size: 12px;
  color: var(--gray-400);
}

.logout-btn-wrap {
  padding: 20px 16px 0;
}

:deep(.van-cell-group--inset) {
  margin: 0;
  border-radius: 12px;
}
</style>