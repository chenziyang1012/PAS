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
        <PreviewImage v-for="img in product.images" :key="img.id" :src="img.url" style="margin-right:8px;vertical-align:top" />
      </div>

      <div style="margin-top:24px;display:flex;gap:12px">
        <el-button type="success" :loading="saving" @click="approve">审核通过</el-button>
        <el-button type="danger" :loading="saving" @click="openReject">审核驳回</el-button>
        <el-button @click="router.back()">返回</el-button>
      </div>
    </template>

    <el-dialog v-model="rejectVisible" title="驳回原因" width="420px">
      <el-form label-width="80px">
        <el-form-item label="驳回类型">
          <el-radio-group v-model="rejectType">
            <el-radio-button value="done">已做产品</el-radio-button>
            <el-radio-button value="infringe">侵权产品</el-radio-button>
            <el-radio-button value="other">其他</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="驳回原因">
          <el-input v-model="rejectReason" type="textarea" :rows="4" :placeholder="rejectType==='other'?'请填写驳回原因（必填）':'选填'" />
        </el-form-item>
      </el-form>
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
import PreviewImage from '@/components/PreviewImage.vue'

const route = useRoute()
const router = useRouter()
const product = ref<any>(null)
const loading = ref(false)
const saving = ref(false)
const rejectVisible = ref(false)
const rejectReason = ref('')
const rejectType = ref<'done'|'infringe'|'other'>('done')

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

function openReject() { rejectReason.value = ''; rejectType.value = 'done'; rejectVisible.value = true }

async function doReject() {
  if (rejectType.value === 'other' && !rejectReason.value.trim()) return ElMessage.warning('选择其他时驳回原因必填')
  saving.value = true
  try {
    await reviewApi.reject(Number(route.params.id), rejectReason.value, rejectType.value)
    ElMessage.success('已驳回')
    router.push('/reviews')
  } catch (e: any) { ElMessage.error(e) } finally { saving.value = false; rejectVisible.value = false }
}
</script>
