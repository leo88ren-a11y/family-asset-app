import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const isLoggedIn = ref(!!token.value)

  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
    isLoggedIn.value = true
  }

  function setUserInfo(info) {
    userInfo.value = info
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    isLoggedIn.value = false
    localStorage.removeItem('token')
  }

  async function restoreSession() {
    if (!token.value) return
    try {
      const res = await authApi.getMe()
      setUserInfo(res)
    } catch (e) {
      logout()
    }
  }

  return { token, userInfo, isLoggedIn, setToken, setUserInfo, logout, restoreSession }
})
