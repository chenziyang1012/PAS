<template>
  <div>
    <el-card>
      <div style="margin-bottom:16px">
        <el-input v-model="query.keyword" placeholder="产品名称" clearable style="width:200px" @change="load" />
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="product_name" label="产品名称" />
        <el-table-column prop="category" label="类目" width="100" />
        <el-table-column label="创建人" width="100">
          <template #default="{row}">{{ row.creator?.real_name }}</template>
        </el-table-column>
        <el-table-column prop="submit_time" label="提交时间" width="160">
          <template #default="{row}">{{ row.submit_time?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{row}">
            <el-button size="small" @click="router.push(`/reviews/${row.id}`)">审核详情</el-button>
            <el-button size="small" type="success" @click="approve(row)">通过</el-button>
            <el-button size="small" type="danger" @click="reject(row)">驳回</el-button>
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
import { reviewApi } from '@/api'

const router = useRouter()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ page: 1, keyword: '' })

async function load() {
  loading.value = true
  try {
    const res: any = await reviewApi.listPending({ ...query, page_size: 20 })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

async function approve(row: any) {
  await ElMessageBox.confirm('确认审核通过？')
  await reviewApi.approve(row.id)
  ElMessage.success('已通过')
  load()
}

async function reject(row: any) {
  const { value } = await ElMessageBox.prompt('请填写驳回原因', '审核驳回', { inputType: 'textarea' })
  if (!value?.trim()) return ElMessage.warning('驳回原因必填')
  await reviewApi.reject(row.id, value)
  ElMessage.success('已驳回')
  load()
}

onMounted(load)
</script>
