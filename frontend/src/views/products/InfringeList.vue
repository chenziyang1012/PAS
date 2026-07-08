<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-input v-model="query.keyword" placeholder="搜索产品名称" clearable style="width:160px" @change="load" />
          <el-input v-model="query.creator_username" placeholder="选品员用户名" clearable style="width:130px" @change="load" />
          <el-date-picker v-model="dateRange" type="daterange" range-separator="~" start-placeholder="标记开始" end-placeholder="标记结束" style="width:220px" @change="onDateChange" value-format="YYYY-MM-DD" />
        </div>
        <el-button v-if="auth.user?.role!=='reviewer'" @click="bulkImportVisible=true">批量导入链接</el-button>
      </div>

      <div v-if="selected.length" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span style="color:#606266">已选 {{ selected.length }} 项</span>
        <el-button v-if="auth.user?.role==='reviewer'||auth.user?.role==='admin'" size="small" type="danger" @click="batchDelete">批量删除</el-button>
      </div>

      <el-table :data="list" v-loading="loading" @selection-change="selected=$event">
        <el-table-column type="selection" width="45" />
        <el-table-column label="主图" width="80">
          <template #default="{row}">
            <el-image v-if="row.main_image || row.images?.[0]?.url"
              :src="row.main_image || row.images[0].url"
              :preview-src-list="[row.main_image || row.images[0].url]"
              style="width:56px;height:56px;object-fit:cover;border-radius:4px"
              preview-teleported fit="cover" />
            <div v-else style="width:56px;height:56px;background:#f5f7fa;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#c0c4cc;font-size:11px">无图</div>
          </template>
        </el-table-column>
        <el-table-column label="产品名称" min-width="160">
          <template #default="{row}">
            <el-link v-if="row.product_link" :href="row.product_link" target="_blank" type="primary">{{ row.product_name }}</el-link>
            <span v-else>{{ row.product_name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="选品员" width="100">
          <template #default="{row}">{{ row.creator?.username }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="标记时间" width="150">
          <template #default="{row}">{{ row.updated_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/products/${row.id}`)">详情</el-button>
            <el-button v-if="auth.user?.role==='reviewer'||auth.user?.role==='admin'" size="small" type="danger" @click="del(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" :page-size="20" :total="total" @current-change="load" layout="total,prev,pager,next" />
    </el-card>

    <el-dialog v-model="bulkImportVisible" title="批量导入产品链接（侵权）" width="500px">
      <p style="color:#606266;font-size:13px;margin-bottom:8px">每行输入一个产品链接，系统将自动爬取标题和主图，并标记为"侵权"</p>
      <div style="margin-bottom:8px">
        <el-upload :show-file-list="false" accept=".txt" :auto-upload="false" @change="handleTxtChange">
          <el-button size="small">上传 .txt 文件</el-button>
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
import { productApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const selected = ref<any[]>([])
const dateRange = ref<[string, string] | null>(null)
const query = reactive({
  page: 1, keyword: '', creator_username: '',
  date_from: undefined as string | undefined,
  date_to: undefined as string | undefined,
})
const bulkImportVisible = ref(false)
const bulkUrls = ref('')
const bulkLoading = ref(false)

function onDateChange(val: [string, string] | null) {
  query.date_from = val?.[0] || undefined
  query.date_to = val?.[1] || undefined
  load()
}

async function load() {
  loading.value = true
  try {
    const res: any = await productApi.listInfringe({ ...query, page_size: 20 })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

async function del(row: any) {
  await ElMessageBox.confirm('确认删除？')
  await productApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

async function batchDelete() {
  await ElMessageBox.confirm(`确认删除 ${selected.value.length} 个产品？`, '批量删除', { type: 'warning' })
  const ids = selected.value.map((r: any) => r.id)
  await productApi.bulkDelete(ids)
  ElMessage.success('批量删除成功')
  load()
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

async function doBulkImport() {
  const urls = bulkUrls.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (!urls.length) return ElMessage.warning('请输入至少一个链接')
  bulkLoading.value = true
  try {
    const res: any = await productApi.bulkCreate(urls, 'infringe')
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
