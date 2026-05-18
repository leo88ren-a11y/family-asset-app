import axios from 'axios'
import { showToast } from 'vant'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截器 - 自动带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || '网络错误，请稍后重试'
    showToast(msg)
    
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  },
)

export default api

// ===== API 方法 =====

// 认证
export const authApi = {
  sendSms: (phone) => api.post('/auth/sms/send', { phone }),
  login: (phone, code) => api.post('/auth/login', { phone, code }),
  getMe: () => api.get('/auth/me'),
  createFamily: (name) => api.post('/auth/family/create', { name }),
  joinFamily: (inviteCode) => api.post('/auth/family/join', { invite_code: inviteCode }),
}

// 家庭
export const familyApi = {
  getDetail: () => api.get('/family/detail'),
  getMembers: () => api.get('/family/members'),
}

// 资产
export const assetApi = {
  getSummary: () => api.get('/assets/summary'),
  getList: (sortBy) => api.get('/assets/list', { params: { sort_by: sortBy } }),
  create: (data) => api.post('/assets', data),
  update: (id, data) => api.put(`/assets/${id}`, data),
  delete: (id) => api.delete(`/assets/${id}`),
  ocrUpload: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/assets/ocr/upload', formData)
  },
  ocrConfirm: (data) => api.post('/assets/ocr/confirm', data),
}

// 汇率
export const exchangeApi = {
  getRates: (base) => api.get('/exchange/rates', { params: { base } }),
}
