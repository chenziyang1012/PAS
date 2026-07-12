<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-input v-model="query.keyword" placeholder="搜索产品名称" clearable style="width:160px" @change="load" />
          <el-select v-model="query.status" placeholder="状态" clearable style="width:110px" @change="load">
            <el-option label="草稿" value="draft" />
            <el-option label="待审核" value="pending_review" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
          <el-select v-model="query.is_completed" placeholder="是否完成" clearable style="width:110px" @change="load">
            <el-option label="已完成" :value="true" />
            <el-option label="未完成" :value="false" />
          </el-select>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="~" start-placeholder="开始日期" end-placeholder="结束日期" style="width:220px" @change="onDateChange" value-format="YYYY-MM-DD" />
        </div>
        <div style="display:flex;gap:8px">
          <el-button v-if="auth.user?.role!=='reviewer'" @click="bulkImportVisible=true">批量导入链接</el-button>
          <el-button v-if="auth.user?.role!=='reviewer'" type="primary" @click="router.push('/products/new')">新建产品</el-button>
        </div>
      </div>

      <div v-if="selected.length" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span style="color:#606266">已选 {{ selected.length }} 项</span>
        <el-button v-if="auth.user?.role!=='reviewer'" size="small" type="success" @click="batchMarkComplete">批量标记完成</el-button>
        <el-button v-if="auth.user?.role!=='reviewer'" size="small" type="danger" @click="batchDelete">批量删除</el-button>
        <el-button v-if="auth.user?.role!=='reviewer'" size="small" @click="batchSubmit">批量提交审核</el-button>
        <el-button size="small" type="primary" plain @click="exportExcel">导出Excel</el-button>
      </div>

      <el-table :data="list" v-loading="loading" @selection-change="selected=$event">
        <el-table-column type="selection" width="45" />
        <el-table-column label="主图" width="80">
          <template #default="{row}">
            <PreviewImage v-if="row.main_image || row.images?.[0]?.url" :src="row.main_image || row.images[0].url" />
            <div v-else style="width:56px;height:56px;background:#f5f7fa;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#c0c4cc;font-size:11px">无图</div>
          </template>
        </el-table-column>
        <el-table-column label="产品名称" min-width="160">
          <template #default="{row}">
            <el-link v-if="row.product_link" :href="row.product_link" target="_blank" type="primary">{{ row.product_name }}</el-link>
            <span v-else>{{ row.product_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="厂家名称" width="110">
          <template #default="{row}">{{ row.manufacturer || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}"><el-tag :type="statusType[row.status]" size="small">{{ statusLabel[row.status] }}</el-tag></template>
        </el-table-column>
        <el-table-column label="是否完成" width="95">
          <template #default="{row}">
            <el-tag v-if="row.is_completed" type="success" size="small">已完成</el-tag>
            <span v-else-if="auth.user?.role!=='reviewer'" @click="toggleComplete(row)">
              <el-button size="small" :disabled="row.status !== 'approved'">标记完成</el-button>
            </span>
            <el-tag v-else type="info" size="small">未完成</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="{row}">{{ row.created_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/products/${row.id}`)">详情</el-button>
            <template v-if="auth.user?.role!=='reviewer'">
              <el-button v-if="['draft','rejected'].includes(row.status)" size="small" type="primary" @click="router.push(`/products/${row.id}/edit`)">编辑</el-button>
              <el-button v-if="row.status==='draft'" size="small" type="success" @click="submitReview(row)">提交</el-button>
              <el-button v-if="row.status==='draft'" size="small" type="danger" @click="del(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" v-model:page-size="pageSize" :page-sizes="[20,50,100,200]" :total="total" @current-change="load" @size-change="onSizeChange" layout="total,sizes,prev,pager,next,jumper" />
    </el-card>

    <el-dialog v-model="bulkImportVisible" title="批量导入产品链接" width="500px">
      <p style="color:#606266;font-size:13px;margin-bottom:8px">每行输入一个产品链接，系统将自动爬取标题和主图</p>
      <div style="margin-bottom:8px;display:flex;gap:8px">
        <el-upload :show-file-list="false" accept=".txt" :auto-upload="false" @change="handleTxtChange">
          <el-button size="small" icon="Upload">上传 .txt 文件</el-button>
        </el-upload>
        <el-upload :show-file-list="false" accept=".xlsx,.xls" :auto-upload="false" @change="handleExcelChange">
          <el-button size="small" icon="Upload">上传 Excel 文件</el-button>
        </el-upload>
      </div>
      <el-input v-model="bulkUrls" type="textarea" :rows="8" placeholder="https://..." />
      <template #footer>
        <el-button @click="bulkImportVisible=false">取消</el-button>
        <el-button type="primary" :loading="bulkLoading" @click="doBulkImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as XLSX from 'xlsx'
import { productApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PreviewImage from '@/components/PreviewImage.vue'

const router = useRouter()
const auth = useAuthStore()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const selected = ref<any[]>([])
const pageSize = ref(20)
const dateRange = ref<[string, string] | null>(null)
const query = reactive({
  page: 1, keyword: '', status: '',
  is_completed: undefined as boolean | undefined,
  date_from: undefined as string | undefined,
  date_to: undefined as string | undefined,
})
const statusLabel: Record<string,string> = { draft:'草稿', pending_review:'待审核', approved:'已通过', rejected:'已驳回' }
const statusType: Record<string,string> = { draft:'info', pending_review:'warning', approved:'success', rejected:'danger' }
const bulkImportVisible = ref(false)
const bulkUrls = ref('')
const bulkLoading = ref(false)

function onSizeChange() { query.page = 1; load() }

function onDateChange(val: [string, string] | null) {
  query.date_from = val?.[0] || undefined
  query.date_to = val?.[1] || undefined
  load()
}

async function load() {
  loading.value = true
  try {
    const res: any = await productApi.list({ ...query, page_size: pageSize.value })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

async function submitReview(row: any) {
  await ElMessageBox.confirm('确认提交审核？')
  try {
    await productApi.submitReview(row.id)
    ElMessage.success('已提交')
    load()
  } catch (e: any) {
    ElMessage.error(e || '提交失败')
  }
}

async function del(row: any) {
  await ElMessageBox.confirm('确认删除？')
  await productApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

async function toggleComplete(row: any) {
  if (row.status !== 'approved') {
    ElMessageBox.alert('该产品未通过审核，无法标记完成', '提示', { type: 'warning' })
    return
  }
  try {
    await productApi.toggleComplete(row.id)
    row.is_completed = true
    row.special_tag = 'done'
    ElMessage.success('已标记完成')
  } catch (e: any) {
    ElMessage.error(e || '操作失败')
  }
}

async function batchMarkComplete() {
  const ids = selected.value.map((r: any) => r.id)
  const nonApproved = selected.value.filter((r: any) => r.status !== 'approved')
  if (nonApproved.length) {
    return ElMessageBox.alert(`有 ${nonApproved.length} 个产品未通过审核，无法批量标记完成`, '提示', { type: 'warning' })
  }
  try {
    await productApi.bulkComplete(ids)
    selected.value.forEach((r: any) => { r.is_completed = true; r.special_tag = 'done' })
    ElMessage.success('批量标记完成成功')
  } catch (e: any) {
    ElMessage.error(e || '操作失败')
  }
}

async function batchDelete() {
  await ElMessageBox.confirm(`确认删除 ${selected.value.length} 个产品？`, '批量删除', { type: 'warning' })
  const ids = selected.value.map((r: any) => r.id)
  await productApi.bulkDelete(ids)
  ElMessage.success('批量删除成功')
  load()
}

async function batchSubmit() {
  const draftRows = selected.value.filter((r: any) => r.status === 'draft')
  if (!draftRows.length) return ElMessage.warning('没有可提交的产品')
  await ElMessageBox.confirm(`确认提交 ${draftRows.length} 个产品审核？`)
  let ok = 0, fail = 0
  await Promise.allSettled(draftRows.map(async (r: any) => {
    try { await productApi.submitReview(r.id); ok++ } catch { fail++ }
  }))
  if (ok) ElMessage.success(`成功提交 ${ok} 个`)
  if (fail) ElMessage.warning(`${fail} 个提交失败（缺少图片等）`)
  load()
}

function exportExcel() {
  const rows = selected.value.map((r: any) => ({
    '产品名称': r.product_name,
    '产品链接': r.product_link || '',
    '厂家名称': r.manufacturer || '',
    '状态': statusLabel[r.status] || r.status,
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '产品列表')
  XLSX.writeFile(wb, `产品导出_${new Date().toLocaleDateString('zh-CN').replace(/\//g,'-')}.xlsx`)
}

function handleTxtChange(file: any) {
  const f: File = file.raw
  if (!f) return
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target?.result as string
    const extra = text.split(/\r?\n/).map(s => s.trim()).filter(Boolean).join('\n')
    bulkUrls.value = bulkUrls.value ? bulkUrls.value + '\n' + extra : extra
  }
  reader.readAsText(f)
}

function handleExcelChange(file: any) {
  const f: File = file.raw
  if (!f) return
  const reader = new FileReader()
  reader.onload = (e) => {
    const data = new Uint8Array(e.target?.result as ArrayBuffer)
    const wb = XLSX.read(data, { type: 'array' })
    const ws = wb.Sheets[wb.SheetNames[0]]
    const rows: any[][] = XLSX.utils.sheet_to_json(ws, { header: 1 })
    const urls: string[] = []
    for (const row of rows) {
      for (const cell of row) {
        const val = String(cell || '').trim()
        if (val.startsWith('http://') || val.startsWith('https://')) {
          urls.push(val)
        }
      }
    }
    if (!urls.length) return ElMessage.warning('Excel 中未找到链接')
    const extra = urls.join('\n')
    bulkUrls.value = bulkUrls.value ? bulkUrls.value + '\n' + extra : extra
  }
  reader.readAsArrayBuffer(f)
}

async function doBulkImport() {
  const urls = bulkUrls.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (!urls.length) return ElMessage.warning('请输入至少一个链接')
  bulkLoading.value = true
  try {
    const res: any = await productApi.bulkCreate(urls)
    ElMessage.success(`成功导入 ${res.data.created} 个产品`)
    bulkImportVisible.value = false
    bulkUrls.value = ''
    load()
  } catch (e: any) {
    ElMessage.error(e || '导入失败')
  } finally {
    bulkLoading.value = false
  }
}

let _timer: ReturnType<typeof setInterval>
onMounted(() => { load(); _timer = setInterval(load, 15000) })
onUnmounted(() => clearInterval(_timer))
</script>
