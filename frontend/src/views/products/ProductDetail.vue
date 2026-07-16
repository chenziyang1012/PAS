<template>
  <el-card v-loading="loading">
    <template v-if="product">
      <el-descriptions :title="product.product_name" :column="2" border>
        <el-descriptions-item label="产品名称">{{ product.product_name }}</el-descriptions-item>
        <el-descriptions-item label="产品类目">{{ product.category }}</el-descriptions-item>
        <el-descriptions-item label="产品链接"><a :href="product.product_link" target="_blank">{{ product.product_link }}</a></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="statusType[product.status]">{{ statusLabel[product.status] }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="创建人">{{ product.creator?.real_name }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ product.created_at?.slice(0,19).replace('T',' ') }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ product.submit_time?.slice(0,19).replace('T',' ') }}</el-descriptions-item>
        <el-descriptions-item label="产品描述" :span="2">{{ product.description }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top:16px">
        <div style="font-weight:bold;margin-bottom:8px">产品图片</div>
        <PreviewImage v-for="img in product.images" :key="img.id" :src="img.url" style="margin-right:8px;vertical-align:top" />
      </div>

      <!-- 已做产品可修改产品ID -->
      <div v-if="product.special_tag === 'done'" style="margin-top:20px;display:flex;align-items:center;gap:8px">
        <span style="font-weight:bold;white-space:nowrap">产品ID：</span>
        <el-input v-model="editProductCode" style="width:200px" placeholder="填写公司产品ID" clearable />
        <el-button type="primary" size="small" :loading="savingCode" @click="saveProductCode">保存</el-button>
      </div>

      <template v-if="product.reviews?.length">
        <div style="margin-top:24px;font-weight:bold">审核记录</div>
        <el-timeline style="margin-top:12px">
          <el-timeline-item v-for="r in product.reviews" :key="r.id" :type="r.result==='approved'?'success':'danger'" :timestamp="r.created_at?.slice(0,19).replace('T',' ')">
            <el-tag :type="r.result==='approved'?'success':'danger'">{{ r.result==='approved'?'通过':'驳回' }}</el-tag>
            <span style="margin-left:8px">{{ r.reviewer?.real_name }}</span>
            <div v-if="r.reason" style="margin-top:4px;color:#f56c6c">驳回原因：{{ r.reason }}</div>
          </el-timeline-item>
        </el-timeline>
      </template>

      <div style="margin-top:24px">
        <el-button @click="router.back()">返回</el-button>
      </div>
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { productApi } from '@/api'
import PreviewImage from '@/components/PreviewImage.vue'

const route = useRoute()
const router = useRouter()
const product = ref<any>(null)
const loading = ref(false)
const editProductCode = ref('')
const savingCode = ref(false)
const statusLabel: Record<string,string> = { draft:'草稿', pending_review:'待审核', approved:'已通过', rejected:'已驳回' }
const statusType: Record<string,string> = { draft:'info', pending_review:'warning', approved:'success', rejected:'danger' }

onMounted(async () => {
  loading.value = true
  try {
    const res: any = await productApi.get(Number(route.params.id))
    product.value = res.data
    editProductCode.value = res.data.product_code || ''
  } finally { loading.value = false }
})

async function saveProductCode() {
  savingCode.value = true
  try {
    await productApi.updateProductCode(Number(route.params.id), editProductCode.value)
    product.value.product_code = editProductCode.value || null
    ElMessage.success('产品ID已保存')
  } catch (e: any) { ElMessage.error(e || '保存失败') }
  finally { savingCode.value = false }
}
</script>
