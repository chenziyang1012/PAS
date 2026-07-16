<template>
  <div>
    <el-card>
      <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
        <el-input v-model="query.keyword" placeholder="产品名称" clearable style="width:180px" @change="filterLoad" />
        <el-select v-if="auth.user?.role !== 'selector'" v-model="query.creator_id" placeholder="选品员" clearable style="width:120px" @change="filterLoad">
          <el-option v-for="u in selectors" :key="u.id" :label="u.username" :value="u.id" />
        </el-select>
      </div>

      <div v-if="selected.length" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span style="color:#606266">已选 {{ selected.length }} 项</span>
        <el-button size="small" type="success" @click="batchApprove">批量通过</el-button>
        <el-button size="small" type="danger" @click="openBatchReject">批量驳回</el-button>
        <el-button size="small" type="warning" @click="batchAiReview">批量AI审核</el-button>
      </div>

      <el-table :data="list" v-loading="loading" @selection-change="selected=$event">
        <el-table-column type="selection" width="45" />
        <el-table-column label="主图" width="80">
          <template #default="{row}">
            <PreviewImage v-if="row.main_image || row.images?.[0]?.url"
              :src="row.main_image || row.images[0].url" />
            <div v-else style="width:56px;height:56px;background:#f5f7fa;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#c0c4cc;font-size:11px">无图</div>
          </template>
        </el-table-column>
        <el-table-column label="产品名称" min-width="160">
          <template #default="{row}">
            <el-link v-if="row.product_link" :href="row.product_link" target="_blank" type="primary">{{ row.product_name }}</el-link>
            <span v-else>{{ row.product_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="选品员" width="90">
          <template #default="{row}">{{ row.creator?.username }}</template>
        </el-table-column>
        <el-table-column prop="submit_time" label="提交时间" width="150">
          <template #default="{row}">{{ row.submit_time?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="AI结论" width="90">
          <template #default="{row}">
            <el-tag v-if="isPendingAi(row)" type="info" size="small" style="animation:pulse 1.5s infinite">审核中</el-tag>
            <template v-else-if="row.ai_review_result">
              <el-tag v-if="riskLevel(row)==='低'" type="success" size="small">低风险</el-tag>
              <el-tag v-else-if="riskLevel(row)==='高'" type="danger" size="small">高风险</el-tag>
              <el-tag v-else-if="riskLevel(row)==='error'" type="danger" size="small">失败</el-tag>
              <el-tag v-else type="warning" size="small">中风险</el-tag>
            </template>
            <span v-else style="color:#c0c4cc;font-size:12px">未审核</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/reviews/${row.id}`)">详情</el-button>
            <el-button size="small" type="warning" @click="openAiDialog(row)">AI审核</el-button>
            <el-button size="small" type="success" @click="approve(row)">通过</el-button>
            <el-button size="small" type="danger" @click="openReject(row)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" v-model:page-size="pageSize" :page-sizes="[20,50,100,200]" :total="total" @current-change="load" @size-change="onSizeChange" layout="total,sizes,prev,pager,next,jumper" />
    </el-card>

    <el-dialog v-model="rejectVisible" title="驳回审核" width="420px" @closed="resetRejectForm">
      <el-form label-width="80px">
        <el-form-item label="驳回类型">
          <el-select v-model="rejectForm.type" style="width:100%">
            <el-option label="侵权" value="infringe" />
            <el-option label="已做" value="done" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="驳回原因">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="补充说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectVisible=false">取消</el-button>
        <el-button type="danger" :loading="rejectLoading" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="aiDialogVisible" title="AI 辅助审核" width="780px" :before-close="closeAiDialog">
      <div v-if="aiDialogProduct">
        <div style="display:flex;gap:12px;margin-bottom:16px;align-items:flex-start">
          <PreviewImage v-if="aiDialogProduct.main_image || aiDialogProduct.images?.[0]?.url"
            :src="aiDialogProduct.main_image || aiDialogProduct.images[0].url" style="flex-shrink:0" />
          <div v-else style="width:56px;height:56px;background:#f5f7fa;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#c0c4cc;font-size:11px;flex-shrink:0">无图</div>
          <div style="flex:1;min-width:0">
            <div style="font-weight:bold;font-size:15px;margin-bottom:6px;word-break:break-all">
              <el-link v-if="aiDialogProduct.product_link" :href="aiDialogProduct.product_link" target="_blank" type="primary">{{ aiDialogProduct.product_name }}</el-link>
              <span v-else>{{ aiDialogProduct.product_name }}</span>
            </div>
            <div style="color:#606266;font-size:13px">选品员：{{ aiDialogProduct.creator?.username }}</div>
            <div style="color:#606266;font-size:13px">提交时间：{{ aiDialogProduct.submit_time?.slice(0,19).replace('T',' ') }}</div>
          </div>
        </div>
        <el-divider style="margin:12px 0" />
        <div style="margin-bottom:10px;font-weight:bold">AI 审核提示词</div>
        <el-input v-model="aiPrompt" type="textarea" :rows="6" placeholder="输入发给AI的审核提示词（留空将使用系统默认提示词）" style="margin-bottom:12px" />
        <el-button type="primary" :loading="aiLoading" @click="triggerAiReview">
          {{ aiLoading ? '正在审核...' : '触发 AI 审核' }}
        </el-button>
        <div style="margin-top:14px">
          <div style="font-weight:bold;margin-bottom:6px">AI 审核结果</div>
          <div v-if="aiLoading" style="color:#909399;font-size:13px">AI 正在分析，请稍候...</div>
          <div v-else-if="aiResult" class="ai-result-body" v-html="aiResultHtml"></div>
          <div v-else style="color:#909399;font-size:13px">暂无 AI 审核结果</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="closeAiDialog">关闭</el-button>
        <el-button type="success" @click="approveFromDialog">通过</el-button>
        <el-button type="danger" @click="openRejectFromDialog">驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import { reviewApi, aiReviewApi, userApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PreviewImage from '@/components/PreviewImage.vue'

const router = useRouter()
const auth = useAuthStore()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const selected = ref<any[]>([])
const selectors = ref<any[]>([])
const pageSize = ref(20)
const query = reactive({ page: 1, keyword: '', creator_id: undefined as number | undefined })

const rejectVisible = ref(false)
const rejectLoading = ref(false)
const rejectTargetIds = ref<number[]>([])
const rejectForm = reactive({ type: 'other', reason: '' })

const aiResultHtml = computed(() => aiResult.value ? marked(aiResult.value) as string : '')

const pendingAiIds = ref<number[]>([])
let _batchPollTimer: ReturnType<typeof setInterval> | null = null

function isPendingAi(row: any): boolean {
  return pendingAiIds.value.includes(row.id)
}

function riskLevel(row: any): '低' | '中' | '高' | 'error' | null {
  const r = row.ai_review_result
  if (!r) return null
  if (r.startsWith('AI审核失败') || r.startsWith('无法审核')) return 'error'
  const m = r.match(/【(低|中|高)】/)
  if (m) return m[1] as '低' | '中' | '高'
  if (/高[风险度]|高度风险/.test(r)) return '高'
  if (/低[风险度]|低度风险/.test(r)) return '低'
  return '中'
}

const aiDialogVisible = ref(false)
const aiDialogProduct = ref<any>(null)
const aiPrompt = ref('')
const aiLoading = ref(false)
const aiResult = ref<string | null>(null)
let _aiPollTimer: ReturnType<typeof setInterval> | null = null

async function load() {
  loading.value = true
  try {
    const res: any = await reviewApi.listPending({ ...query, page_size: pageSize.value })
    list.value = res.data.items; total.value = res.data.total
  } catch (e: any) {
    ElMessage.error(e || '加载失败')
  } finally { loading.value = false }
}

function onSizeChange() { query.page = 1; load() }

function filterLoad() { query.page = 1; load() }

async function silentRefresh() {
  if (rejectVisible.value || aiDialogVisible.value) return
  try {
    const res: any = await reviewApi.listPending({ ...query, page_size: pageSize.value })
    const incoming = JSON.stringify(res.data.items)
    if (incoming !== JSON.stringify(list.value)) {
      const _map = new Map(list.value.map((r: any) => [r.id, r]))
      list.value = res.data.items.map((row: any) => {
        const ex = _map.get(row.id)
        if (ex) { Object.assign(ex, row); return ex }
        return row
      })
      total.value = res.data.total
    }
  } catch {}
}

async function loadSelectors() {
  if (auth.user?.role === 'selector') return
  const res: any = await userApi.listSelectors()
  selectors.value = res.data?.items || []
}

async function approve(row: any) {
  await ElMessageBox.confirm('确认审核通过？')
  await reviewApi.approve(row.id)
  ElMessage.success('已通过')
  load()
}

function openReject(row: any) {
  rejectTargetIds.value = [row.id]
  rejectVisible.value = true
}

function openBatchReject() {
  rejectTargetIds.value = selected.value.map((r: any) => r.id)
  rejectVisible.value = true
}

function resetRejectForm() {
  rejectForm.type = 'other'
  rejectForm.reason = ''
  rejectTargetIds.value = []
}

async function doReject() {
  rejectLoading.value = true
  try {
    const reason = rejectForm.reason || { infringe: '侵权', done: '已做', other: '其他原因' }[rejectForm.type] || ''
    await Promise.all(rejectTargetIds.value.map(id =>
      reviewApi.reject(id, reason, rejectForm.type)
    ))
    ElMessage.success('驳回成功')
    rejectVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e || '操作失败')
  } finally {
    rejectLoading.value = false
  }
}

async function batchApprove() {
  await ElMessageBox.confirm(`确认批量通过 ${selected.value.length} 个产品？`)
  await Promise.all(selected.value.map((r: any) => reviewApi.approve(r.id)))
  ElMessage.success('批量通过成功')
  load()
}

function openAiDialog(row: any) {
  aiDialogProduct.value = row
  aiResult.value = row.ai_review_result || null
  aiLoading.value = false
  aiPrompt.value = ''
  aiDialogVisible.value = true
  aiReviewApi.getDoubaoSettings().then((res: any) => {
    if (res.data?.prompt && !aiPrompt.value) aiPrompt.value = res.data.prompt
  }).catch(() => {})
  // 拉取最新结果，如果正在处理中则自动轮询
  aiReviewApi.getResult(row.id).then((res: any) => {
    const d = res.data
    if (d.ai_review_result) aiResult.value = d.ai_review_result
    if (d.is_pending) {
      aiLoading.value = true
      _aiPollTimer = setInterval(async () => {
        try {
          const r: any = await aiReviewApi.getResult(aiDialogProduct.value.id)
          if (!r.data.is_pending) {
            clearInterval(_aiPollTimer!); _aiPollTimer = null
            aiLoading.value = false
            aiResult.value = r.data.ai_review_result
          }
        } catch {}
      }, 2000)
    }
  }).catch(() => {})
}

function closeAiDialog(done?: () => void) {
  if (_aiPollTimer) { clearInterval(_aiPollTimer); _aiPollTimer = null }
  aiDialogVisible.value = false
  if (done) done()
}

async function triggerAiReview() {
  if (!aiDialogProduct.value) return
  aiLoading.value = true
  if (_aiPollTimer) { clearInterval(_aiPollTimer); _aiPollTimer = null }
  try {
    await aiReviewApi.triggerReview(aiDialogProduct.value.id, aiPrompt.value || undefined)
    _aiPollTimer = setInterval(async () => {
      try {
        const res: any = await aiReviewApi.getResult(aiDialogProduct.value.id)
        if (!res.data.is_pending) {
          clearInterval(_aiPollTimer!); _aiPollTimer = null
          aiLoading.value = false
          aiResult.value = res.data.ai_review_result
        }
      } catch {}
    }, 2000)
    setTimeout(() => {
      if (aiLoading.value) {
        if (_aiPollTimer) { clearInterval(_aiPollTimer); _aiPollTimer = null }
        aiLoading.value = false
        ElMessage.warning('AI审核超时，请稍后重试')
      }
    }, 120000)
  } catch (e: any) {
    aiLoading.value = false
    ElMessage.error(e || 'AI审核触发失败')
  }
}

async function approveFromDialog() {
  const product = aiDialogProduct.value
  if (!product) return
  try {
    await ElMessageBox.confirm('确认审核通过？')
    await reviewApi.approve(product.id)
    ElMessage.success('已通过')
    closeAiDialog()
    load()
  } catch {}
}

function openRejectFromDialog() {
  if (!aiDialogProduct.value) return
  closeAiDialog()
  openReject(aiDialogProduct.value)
}

async function batchAiReview() {
  const ids = selected.value.map((r: any) => r.id)
  if (!ids.length) return
  try {
    await aiReviewApi.batchTrigger(ids)
    pendingAiIds.value = [...new Set([...pendingAiIds.value, ...ids])]
    ElMessage.success(`已触发 ${ids.length} 个产品的 AI 审核`)
    if (!_batchPollTimer) {
      _batchPollTimer = setInterval(async () => {
        try {
          const res: any = await reviewApi.listPending({ ...query, page_size: pageSize.value })
          const items: any[] = res.data.items
          if (!rejectVisible.value && !aiDialogVisible.value) {
            const _map = new Map(list.value.map((r: any) => [r.id, r]))
            list.value = items.map((row: any) => {
              const ex = _map.get(row.id)
              if (ex) { Object.assign(ex, row); return ex }
              return row
            })
            total.value = res.data.total
          }
          pendingAiIds.value = pendingAiIds.value.filter(id => {
            const row = items.find((r: any) => r.id === id)
            return !row || !row.ai_review_result
          })
        } catch {}
        if (pendingAiIds.value.length === 0) {
          clearInterval(_batchPollTimer!); _batchPollTimer = null
        }
      }, 3000)
    }
  } catch (e: any) {
    ElMessage.error(e || '批量AI审核触发失败')
  }
}

let _timer: ReturnType<typeof setInterval>
watch([() => query.page, pageSize, () => query.keyword, () => query.creator_id], () => {
  sessionStorage.setItem('pag:reviews', JSON.stringify({ page: query.page, pageSize: pageSize.value, keyword: query.keyword, creator_id: query.creator_id }))
})
onMounted(() => {
  const saved = sessionStorage.getItem('pag:reviews')
  if (saved) {
    const p = JSON.parse(saved)
    query.page = p.page; pageSize.value = p.pageSize
    query.keyword = p.keyword || ''
    query.creator_id = p.creator_id ?? undefined
  }
  load(); loadSelectors(); _timer = setInterval(silentRefresh, 15000)
})
onUnmounted(() => {
  clearInterval(_timer)
  if (_aiPollTimer) clearInterval(_aiPollTimer)
  if (_batchPollTimer) clearInterval(_batchPollTimer)
})
</script>

<style scoped>
.ai-result-body {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.7;
  max-height: 360px;
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
.ai-result-body :deep(th:first-child),
.ai-result-body :deep(td:first-child),
.ai-result-body :deep(th:nth-child(2)),
.ai-result-body :deep(td:nth-child(2)) {
  white-space: nowrap;
}
.ai-result-body :deep(th) {
  background: #ebeef5;
  font-weight: bold;
}
.ai-result-body :deep(p) { margin: 4px 0; }
.ai-result-body :deep(strong) { font-weight: bold; }
</style>
