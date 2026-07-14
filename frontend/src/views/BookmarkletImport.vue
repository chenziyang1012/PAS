<template>
  <div style="max-width:600px;margin:40px auto;text-align:center">
    <el-card v-loading="loading">
      <template v-if="status === 'loading'">
        <el-icon :size="48" style="color:#409EFF"><Loading /></el-icon>
        <p style="margin-top:16px;font-size:16px">正在导入产品...</p>
      </template>
      <template v-else-if="status === 'success'">
        <el-icon :size="48" style="color:#67C23A"><CircleCheckFilled /></el-icon>
        <p style="margin-top:16px;font-size:16px">产品导入成功！</p>
        <p style="color:#909399">此窗口将自动关闭</p>
      </template>
      <template v-else-if="status === 'error'">
        <el-icon :size="48" style="color:#F56C6C"><CircleCloseFilled /></el-icon>
        <p style="margin-top:16px;font-size:16px;color:#F56C6C">导入失败</p>
        <p style="color:#909399">{{ errorMsg }}</p>
        <el-button style="margin-top:16px" @click="router.push('/products')">返回列表</el-button>
      </template>
      <template v-else>
        <p>无效的导入请求</p>
        <el-button style="margin-top:16px" @click="router.push('/products')">返回列表</el-button>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { productApi } from '@/api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const status = ref<'loading' | 'success' | 'error' | 'invalid'>('invalid')
const errorMsg = ref('')

function notifyOpener(ok: boolean, name: string, err: string) {
  try {
    // Broadcast to all same-origin tabs (e.g. ProductList)
    const bc = new BroadcastChannel('pas_import')
    bc.postMessage({ type: 'prs_result', ok, name, err })
    bc.close()
    // Also notify the opener tab if available
    if (window.opener) {
      window.opener.postMessage({ type: 'prs_result', ok, name, err }, '*')
      setTimeout(() => { try { window.close() } catch {} }, 500)
    }
  } catch {}
}

onMounted(async () => {
  const q = route.query
  if (!q.title && !q.url) {
    status.value = 'invalid'
    return
  }
  status.value = 'loading'
  loading.value = true
  try {
    const res: any = await productApi.fromBookmarklet({
      product_name: q.title || q.url || '',
      product_link: q.url || '',
      main_image: q.image || '',
      manufacturer: q.manufacturer || '',
      category: q.tag || null,
    })
    status.value = 'success'
    notifyOpener(true, String(q.title || '').substring(0, 40), '')
  } catch (e: any) {
    errorMsg.value = e || '导入失败'
    status.value = 'error'
    notifyOpener(false, '', String(e || '导入失败'))
  } finally {
    loading.value = false
  }
})
</script>
