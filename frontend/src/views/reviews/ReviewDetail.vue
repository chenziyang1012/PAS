<template>
  <el-card v-loading="loading">
    <template v-if="product">
      <el-descriptions :title="product.product_name" :column="2" border>
        <el-descriptions-item label="产品名称">{{ product.product_name }}</el-descriptions-item>
        <el-descriptions-item label="类目">{{ product.category }}</el-descriptions-item>
        <el-descriptions-item label="产品链接"><a :href="product.product_link" target="_blank">{{ product.product_link }}</a></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag type="warning">待审核</el-tag></el-descriptions-item>
        <el-descriptions-item label="创建人">{{ product.creator?.real_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ product.created_at?.slice(0,19).replace('T',' ') }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ product.submit_time?.slice(0,19).replace('T',' ') }}</el-descriptions-item>
        <el-descriptions-item label="产品描述" :span="2">{{ product.description }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top:16px">
        <div style="font-weight:bold;margin-bottom:8px">产品图片</div>
        <el-image v-for="img in product.images" :key="img.id" :src="img.url" style="width:120px;height:120px;margin-right:8px" fit="cover" :preview-src-list="product.images.map((i:any)=>i.url)" />
      </div>

      <div style="margin-top:24px;display:flex;gap:12px">
        <el-button type="success" :loading="saving" @click="approve">审核通过</el-button>
        <el-button type="danger" :loading="saving" @click="openReject">审核驳回</el-button>
        <el-button @click="router.back()">返回</el-button>
      </div>
    </template>

    <el-dialog v-model="rejectVisible" title="驳回原因" width="400px">
      <el-input v-model="rejectReason" type="textarea" :rows="4" placeholder="请填写驳回原因（必填）" />
      <template #footer>
        <el-button @click="rejectVisible=false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="doReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { reviewApi } from '@/api'

const route = useRoute()
const router = useRouter()
const product = ref<any>(null)
const loading = ref(false)
const saving = ref(false)
const rejectVisible = ref(false)
const rejectReason = ref('')

onMounted(async () => {
  loading.value = true
  try {
    const res: any = await reviewApi.detail(Number(route.params.id))
    product.value = res.data
  } finally { loading.value = false }
})

async function approve() {
  saving.value = true
  try {
    await reviewApi.approve(Number(route.params.id))
    ElMessage.success('审核通过')
    router.push('/reviews')
  } catch (e: any) { ElMessage.error(e) } finally { saving.value = false }
}

function openReject() { rejectReason.value = ''; rejectVisible.value = true }

async function doReject() {
  if (!rejectReason.value.trim()) return ElMessage.warning('驳回原因必填')
  saving.value = true
  try {
    await reviewApi.reject(Number(route.params.id), rejectReason.value)
    ElMessage.success('已驳回')
    router.push('/reviews')
  } catch (e: any) { ElMessage.error(e) } finally { saving.value = false; rejectVisible.value = false }
}
</script>
