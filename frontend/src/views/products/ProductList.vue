<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px">
        <div style="display:flex;gap:8px">
          <el-input v-model="query.keyword" placeholder="产品名称" clearable style="width:200px" @change="load" />
          <el-select v-model="query.status" placeholder="状态" clearable style="width:130px" @change="load">
            <el-option label="草稿" value="draft" /><el-option label="待审核" value="pending_review" />
            <el-option label="已通过" value="approved" /><el-option label="已驳回" value="rejected" />
          </el-select>
        </div>
        <el-button v-if="auth.user?.role!=='reviewer'" type="primary" @click="router.push('/products/new')">新建产品</el-button>
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="product_name" label="产品名称" />
        <el-table-column prop="category" label="类目" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{row}"><el-tag :type="statusType[row.status]">{{ statusLabel[row.status] }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{row}">{{ row.created_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column prop="submit_time" label="提交时间" width="160">
          <template #default="{row}">{{ row.submit_time?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/products/${row.id}`)">详情</el-button>
            <template v-if="auth.user?.role!=='reviewer'">
              <el-button v-if="['draft','rejected'].includes(row.status)" size="small" type="primary" @click="router.push(`/products/${row.id}/edit`)">编辑</el-button>
              <el-button v-if="['draft','rejected'].includes(row.status)" size="small" type="success" @click="submitReview(row)">提交审核</el-button>
              <el-button v-if="row.status==='draft'" size="small" type="danger" @click="del(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" :page-size="20" :total="total" @current-change="load" layout="total,prev,pager,next" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { productApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ page: 1, keyword: '', status: '' })
const statusLabel: Record<string,string> = { draft:'草稿', pending_review:'待审核', approved:'已通过', rejected:'已驳回' }
const statusType: Record<string,string> = { draft:'info', pending_review:'warning', approved:'success', rejected:'danger' }

async function load() {
  loading.value = true
  try {
    const res: any = await productApi.list({ ...query, page_size: 20 })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

async function submitReview(row: any) {
  await ElMessageBox.confirm('确认提交审核？')
  await productApi.submitReview(row.id)
  ElMessage.success('已提交')
  load()
}

async function del(row: any) {
  await ElMessageBox.confirm('确认删除？')
  await productApi.delete(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>
