import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    {
      path: '/',
      component: () => import('@/views/LayoutView.vue'),
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: () => import('@/views/DashboardView.vue') },
        { path: 'users', component: () => import('@/views/UserManagement.vue'), meta: { roles: ['admin'] } },
        { path: 'settings', component: () => import('@/views/SettingsView.vue') },
        { path: 'products', component: () => import('@/views/products/ProductList.vue') },
        { path: 'products/new', component: () => import('@/views/products/ProductForm.vue') },
        { path: 'products/:id/edit', component: () => import('@/views/products/ProductForm.vue') },
        { path: 'products/:id', component: () => import('@/views/products/ProductDetail.vue') },
        { path: 'reviews', component: () => import('@/views/reviews/ReviewList.vue'), meta: { roles: ['reviewer', 'admin'] } },
        { path: 'reviews/:id', component: () => import('@/views/reviews/ReviewDetail.vue'), meta: { roles: ['reviewer', 'admin'] } },
        { path: 'done', component: () => import('@/views/products/DoneList.vue') },
        { path: 'infringe', component: () => import('@/views/products/InfringeList.vue') },
        { path: 'bookmarklet-import', component: () => import('@/views/BookmarkletImport.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const auth = useAuthStore()
  if (!auth.token) return '/login'
  if (!auth.user) {
    try { await auth.fetchMe() } catch { return '/login' }
  }
  if (to.meta.roles && !(to.meta.roles as string[]).includes(auth.user!.role)) return '/dashboard'
  return true
})

export default router
