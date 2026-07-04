import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api'

interface User { id: number; username: string; real_name: string; role: string; status: string }

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref(localStorage.getItem('token') || '')

  async function login(username: string, password: string) {
    const res: any = await authApi.login(username, password)
    token.value = res.data.token
    user.value = res.data.user
    localStorage.setItem('token', res.data.token)
  }

  async function fetchMe() {
    try {
      const res: any = await authApi.me()
      user.value = res.data
    } catch (err) {
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
      throw err
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, login, fetchMe, logout }
})
