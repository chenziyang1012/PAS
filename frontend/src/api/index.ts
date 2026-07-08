import axios from 'axios'

const http = axios.create({ baseURL: '/' })

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(err.response?.data?.detail || '请求失败')
  }
)

export const authApi = {
  login: (username: string, password: string) => http.post('/api/auth/login', { username, password }),
  me: () => http.get('/api/auth/me'),
  logout: () => http.post('/api/auth/logout'),
}

export const userApi = {
  list: (params?: object) => http.get('/api/users', { params }),
  create: (data: object) => http.post('/api/users', data),
  update: (id: number, data: object) => http.put(`/api/users/${id}`, data),
  updateStatus: (id: number, status: string) => http.patch(`/api/users/${id}/status`, { status }),
  resetPassword: (id: number, new_password: string) => http.post(`/api/users/${id}/reset-password`, { new_password }),
  delete: (id: number) => http.delete(`/api/users/${id}`),
}

export const productApi = {
  list: (params?: object) => http.get('/api/products', { params }),
  create: (data: object) => http.post('/api/products', data),
  get: (id: number) => http.get(`/api/products/${id}`),
  update: (id: number, data: object) => http.put(`/api/products/${id}`, data),
  delete: (id: number) => http.delete(`/api/products/${id}`),
  submitReview: (id: number) => http.post(`/api/products/${id}/submit-review`),
  toggleComplete: (id: number) => http.patch(`/api/products/${id}/complete`),
  bulkCreate: (urls: string[], special_tag?: string) => http.post('/api/products/bulk', { urls, special_tag }),
  bulkDelete: (ids: number[]) => http.delete('/api/products/bulk', { data: { ids } }),
  bulkComplete: (ids: number[]) => http.patch('/api/products/bulk-complete', { ids }),
  scrape: (url: string) => http.post('/api/products/scrape', { url }),
  fromBookmarklet: (data: object) => http.post('/api/products/from-bookmarklet', data),
  listDone: (params?: object) => http.get('/api/products/done', { params }),
  listInfringe: (params?: object) => http.get('/api/products/infringe', { params }),
  getCookie1688: () => http.get('/api/products/settings/cookie-1688'),
  setCookie1688: (cookie_1688: string) => http.put('/api/products/settings/cookie-1688', { cookie_1688 }),
  getMyCookie1688: () => http.get('/api/products/my-cookie-1688'),
  setMyCookie1688: (cookie_1688: string) => http.put('/api/products/my-cookie-1688', { cookie_1688 }),
  deleteMyCookie1688: () => http.delete('/api/products/my-cookie-1688'),
}

export const reviewApi = {
  listPending: (params?: object) => http.get('/api/reviews/pending', { params }),
  detail: (productId: number) => http.get(`/api/reviews/${productId}`),
  approve: (productId: number) => http.post(`/api/reviews/${productId}/approve`),
  reject: (productId: number, reason: string, reject_type?: string) => http.post(`/api/reviews/${productId}/reject`, { reason, reject_type }),
}

export const uploadApi = {
  image: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/api/upload/image', form)
  },
}
