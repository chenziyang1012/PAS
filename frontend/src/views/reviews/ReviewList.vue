<template>
  <div>
    <el-card>
      <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
        <el-input v-model="query.keyword" placeholder="产品名称" clearable style="width:180px" @change="load" />
        <el-select v-if="auth.user?.role !== 'selector'" v-model="query.creator_id" placeholder="选品员" clearable style="width:120px" @change="load">
          <el-option v-for="u in selectors" :key="u.id" :label="u.username" :value="u.id" />
        </el-select>
      </div>

      <div v-if="selected.length" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span style="color:#606266">已选 {{ selected.length }} 项</span>
        <el-button size="small" type="success" @click="batchApprove">批量通过</el-button>
        <el-button size="small" type="danger" @click="openBatchReject">批量驳回</el-button>
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
        <el-table-column label="操作" width="220">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/reviews/${row.id}`)">详情</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { reviewApi, userApi } from '@/api'
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

async function silentRefresh() {
  // 驳回对话框打开时跳过
  if (rejectVisible.value) return
  try {
    const res: any = await reviewApi.listPending({ ...query, page_size: pageSize.value })
    const incoming = JSON.stringify(res.data.items)
    if (incoming !== JSON.stringify(list.value)) {
      list.value = res.data.items
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

let _timer: ReturnType<typeof setInterval>
watch([() => query.page, pageSize], () => {
  sessionStorage.setItem('pag:reviews', JSON.stringify({ page: query.page, pageSize: pageSize.value }))
})
onMounted(() => {
  const saved = sessionStorage.getItem('pag:reviews')
  if (saved) { const p = JSON.parse(saved); query.page = p.page; pageSize.value = p.pageSize }
  load(); loadSelectors(); _timer = setInterval(silentRefresh, 15000)
})
onUnmounted(() => { clearInterval(_timer) })
</script>
