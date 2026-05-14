<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="login-logo">
        <div class="logo-icon">💰</div>
        <h1>家庭资产管家</h1>
        <p>一目了然，全家资产尽在掌握</p>
      </div>
    </div>

    <div class="login-form">
      <van-cell-group inset>
        <van-field
          v-model="phone"
          type="tel"
          label="+86"
          placeholder="请输入手机号"
          maxlength="11"
          :rules="[{ pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确' }]"
        />
        <van-field
          v-model="code"
          type="digit"
          placeholder="请输入验证码"
          maxlength="6"
        >
          <template #button>
            <van-button
              size="small"
              type="primary"
              :disabled="countdown > 0 || !phoneValid"
              @click="sendCode"
              :loading="sending"
            >
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </van-button>
          </template>
        </van-field>
      </van-cell-group>

      <div class="login-btn-wrap">
        <van-button
          type="primary"
          block
          round
          size="large"
          :disabled="!phone || code.length < 4"
          :loading="loggingIn"
          @click="handleLogin"
        >
          登录 / 注册
        </van-button>
      </div>

      <p class="login-agree">
        登录即表示同意《用户协议》和《隐私政策》
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { authApi } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const phone = ref('')
const code = ref('')
const sending = ref(false)
const loggingIn = ref(false)
const countdown = ref(0)

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(phone.value))

async function sendCode() {
  if (!phoneValid.value) return
  
  sending.value = true
  try {
    const res = await authApi.sendSms(phone.value)
    
    // 开发模式：显示验证码
    if (res.dev_code) {
      // 自动填充（开发用，生产环境删除）
      // showSuccessToast(`验证码: ${res.dev_code}`)
    }
    
    showSuccessToast('验证码已发送')
    
    // 倒计时
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } finally {
    sending.value = false
  }
}

async function handleLogin() {
  loggingIn.value = true
  try {
    const res = await authApi.login(phone.value, code.value)
    userStore.setToken(res.access_token)
    userStore.setUserInfo(res.user)
    
    showSuccessToast('登录成功')
    
    // 检查是否已加入家庭
    if (!res.user.family_id) {
      router.replace('/profile')
    } else {
      router.replace('/')
    }
  } finally {
    loggingIn.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #3B82F6 0%, #60A5FA 50%, #F5F5F5 50%);
}

.login-bg {
  padding: 80px 24px 48px;
  text-align: center;
  color: white;
}

.logo-icon {
  font-size: 56px;
  margin-bottom: 12px;
}

.login-bg h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.login-bg p {
  font-size: 14px;
  opacity: 0.85;
}

.login-form {
  padding: 20px 16px;
  margin-top: -20px;
}

.login-btn-wrap {
  padding: 24px 4px 8px;
}

.login-agree {
  text-align: center;
  font-size: 12px;
  color: var(--gray-400);
  padding: 12px 0;
}
</style>
