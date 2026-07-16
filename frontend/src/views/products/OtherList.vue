<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-input v-model="query.keyword" placeholder="搜索产品名称" clearable style="width:160px" @change="load" />
          <el-input v-model="query.creator_username" placeholder="选品员用户名" clearable style="width:130px" @change="load" />
          <el-date-picker v-model="dateRange" type="daterange" range-separator="~" start-placeholder="驳回开始" end-placeholder="驳回结束" style="width:220px" @change="onDateChange" value-format="YYYY-MM-DD" />
        </div>
      </div>

      <div v-if="selected.length" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span style="color:#606266">已选 {{ selected.length }} 项</span>
        <el-button v-if="auth.user?.role==='reviewer'||auth.user?.role==='admin'" size="small" type="danger" @click="batchDelete">批量删除</el-button>
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
        <el-table-column label="选品员" width="100">
          <template #default="{row}">{{ row.creator?.username }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="驳回时间" width="150">
          <template #default="{row}">{{ row.updated_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/products/${row.id}`)">详情</el-button>
            <el-button v-if="auth.user?.role==='reviewer'||auth.user?.role==='admin'" size="small" type="danger" @click="del(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" v-model:page-size="pageSize" :page-sizes="[20,50,100,200]" :total="total" @current-change="load" @size-change="onSizeChange" layout="total,sizes,prev,pager,next" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
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
  page: 1, keyword: '', creator_username: '',
  date_from: undefined as string | undefined,
  date_to: undefined as string | undefined,
})

function onSizeChange() { query.page = 1; load() }

function onDateChange(val: [string, string] | null) {
  query.date_from = val?.[0] || undefined
  query.date_to = val?.[1] || undefined
  load()
}

async function load() {
  loading.value = true
  try {
    const res: any = await productApi.listOther({ ...query, page_size: pageSize.value })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

async function silentRefresh() {
  try {
    const res: any = await productApi.listOther({ ...query, page_size: pageSize.value })
    const incoming = JSON.stringify(res.data.items)
    if (incoming !== JSON.stringify(list.value)) {
      list.value = res.data.items
      total.value = res.data.total
    }
  } catch {}
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

let _timer: ReturnType<typeof setInterval>
watch([() => query.page, pageSize], () => {
  sessionStorage.setItem('pag:other', JSON.stringify({ page: query.page, pageSize: pageSize.value }))
})
onMounted(() => {
  const saved = sessionStorage.getItem('pag:other')
  if (saved) { const p = JSON.parse(saved); query.page = p.page; pageSize.value = p.pageSize }
  load(); _timer = setInterval(silentRefresh, 15000)
})
onUnmounted(() => { clearInterval(_timer) })
</script>
