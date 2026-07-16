<template>
  <div style="max-width:640px;margin:40px auto;padding:0 16px">
    <el-card>
      <template v-if="status==='saving'">
        <div style="text-align:center;padding:32px 0">
          <div v-loading="true" style="height:48px" />
          <p style="margin-top:16px;font-size:16px">正在导入产品...</p>
        </div>
      </template>

      <template v-else-if="status==='ai_pending'">
        <div style="text-align:center;padding:32px 0">
          <div v-loading="true" style="height:48px" />
          <p style="margin-top:16px;font-size:16px">AI 正在审核，请稍候...</p>
          <p style="color:#909399;font-size:13px">分析产品侵权风险中</p>
        </div>
      </template>

      <template v-else-if="status==='ai_done'">
        <div style="font-size:14px;font-weight:bold;margin-bottom:12px;word-break:break-all">{{ productName }}</div>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
          <span style="color:#606266;font-size:13px">AI 风险评估：</span>
          <el-tag v-if="aiRisk==='低'" type="success" size="small">低风险</el-tag>
          <el-tag v-else-if="aiRisk==='高'" type="danger" size="small">高风险</el-tag>
          <el-tag v-else-if="aiRisk==='error'" type="danger" size="small">审核失败</el-tag>
          <el-tag v-else type="warning" size="small">中风险</el-tag>
        </div>
        <div class="ai-result-body" v-html="aiResultHtml" />
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px;padding-top:12px;border-top:1px solid #ebeef5">
          <el-button type="danger" plain :loading="canceling" @click="doCancel">取消采集</el-button>
          <el-button type="primary" @click="doSave">保存到系统</el-button>
        </div>
      </template>

      <template v-else-if="status==='success'">
        <div style="text-align:center;padding:32px 0">
          <el-icon :size="48" style="color:#67C23A"><CircleCheckFilled /></el-icon>
          <p style="margin-top:16px;font-size:16px">产品导入成功！</p>
          <p style="color:#909399">此窗口将自动关闭</p>
        </div>
      </template>

      <template v-else-if="status==='error'">
        <div style="text-align:center;padding:32px 0">
          <el-icon :size="48" style="color:#F56C6C"><CircleCloseFilled /></el-icon>
          <p style="margin-top:16px;font-size:16px;color:#F56C6C">导入失败</p>
          <p style="color:#909399">{{ errorMsg }}</p>
          <el-button style="margin-top:16px" @click="router.push('/products')">返回列表</el-button>
        </div>
      </template>

      <template v-else>
        <div style="text-align:center;padding:32px 0">
          <p>无效的导入请求</p>
          <el-button style="margin-top:16px" @click="router.push('/products')">返回列表</el-button>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import { CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { productApi, aiReviewApi } from '@/api'

const route = useRoute()
const router = useRouter()
const status = ref<'saving' | 'ai_pending' | 'ai_done' | 'success' | 'error' | 'invalid'>('invalid')
const errorMsg = ref('')
const productId = ref<number | null>(null)
const productName = ref('')
const aiResult = ref<string | null>(null)
const canceling = ref(false)
let _pollTimer: ReturnType<typeof setInterval> | null = null
let _pollTimeout: ReturnType<typeof setTimeout> | null = null

const aiRisk = computed(() => {
  const r = aiResult.value
  if (!r) return null
  if (r.startsWith('AI审核失败') || r.startsWith('无法审核')) return 'error'
  const m = r.match(/【(低|中|高)】/)
  if (m) return m[1] as '低' | '中' | '高'
  if (/高[风险度]|高度风险/.test(r)) return '高'
  if (/低[风险度]|低度风险/.test(r)) return '低'
  return '中'
})

const aiResultHtml = computed(() => aiResult.value ? marked(aiResult.value) as string : '')

function notifyOpener(ok: boolean, name: string, err: string) {
  try {
    const bc = new BroadcastChannel('pas_import')
    bc.postMessage({ type: 'prs_result', ok, name, err })
    bc.close()
    if (window.opener) window.opener.postMessage({ type: 'prs_result', ok, name, err }, '*')
  } catch {}
}

function closeWindow() {
  setTimeout(() => { try { window.close() } catch {} }, 300)
}

function stopPolling() {
  if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  if (_pollTimeout) { clearTimeout(_pollTimeout); _pollTimeout = null }
}

function startPolling(id: number) {
  _pollTimer = setInterval(async () => {
    try {
      const res: any = await aiReviewApi.getResult(id)
      const d = res.data
      if (!d.is_pending) {
        stopPolling()
        aiResult.value = d.ai_review_result
        status.value = 'ai_done'
      }
    } catch {}
  }, 2000)
  _pollTimeout = setTimeout(() => {
    if (status.value === 'ai_pending') {
      stopPolling()
      aiResult.value = 'AI审核超时，请在审核列表中手动查看结果'
      status.value = 'ai_done'
    }
  }, 120000)
}

async function doSave() {
  notifyOpener(true, productName.value.substring(0, 40), '')
  closeWindow()
}

async function doCancel() {
  if (!productId.value) { closeWindow(); return }
  canceling.value = true
  try { await productApi.delete(productId.value) } catch {}
  notifyOpener(false, '', '用户取消采集')
  closeWindow()
}

onMounted(async () => {
  const q = route.query
  if (!q.title && !q.url) { status.value = 'invalid'; return }
  productName.value = String(q.title || q.url || '')
  status.value = 'saving'
  try {
    const res: any = await productApi.fromBookmarklet({
      product_name: q.title || q.url || '',
      product_link: q.url || '',
      main_image: q.image || '',
      manufacturer: q.manufacturer || '',
      category: q.tag || null,
    })
    const data = res.data
    productId.value = data.id
    if (data.ai_review_queued) {
      status.value = 'ai_pending'
      startPolling(data.id)
    } else {
      status.value = 'success'
      notifyOpener(true, productName.value.substring(0, 40), '')
      closeWindow()
    }
  } catch (e: any) {
    errorMsg.value = e || '导入失败'
    status.value = 'error'
    notifyOpener(false, '', String(e || '导入失败'))
  }
})

onUnmounted(() => { stopPolling() })
</script>

<style scoped>
.ai-result-body {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.7;
  max-height: 320px;
  overflow-y: auto;
}
.ai-result-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.ai-result-body :deep(th),
.ai-result-body :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
  text-align: left;
}
.ai-result-body :deep(th) {
  background: #ebeef5;
  font-weight: bold;
  white-space: nowrap;
}
.ai-result-body :deep(td:first-child) { white-space: nowrap; }
.ai-result-body :deep(p) { margin: 4px 0; }
.ai-result-body :deep(strong) { font-weight: bold; }
</style>
