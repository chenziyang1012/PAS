<template>
  <el-card :title="isEdit ? '编辑产品' : '新建产品'">
    <el-form :model="form" label-width="100px" style="max-width:600px">
      <el-form-item label="产品名称" required>
        <el-input v-model="form.product_name" />
      </el-form-item>
      <el-form-item label="产品链接">
        <el-input v-model="form.product_link" />
      </el-form-item>
      <el-form-item label="产品类目">
        <el-input v-model="form.category" />
      </el-form-item>
      <el-form-item label="产品描述">
        <el-input v-model="form.description" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item label="主图">
        <div style="display:flex;align-items:flex-start;gap:12px">
          <el-image v-if="form.main_image" :src="form.main_image" style="width:80px;height:80px;border-radius:4px;border:1px solid #dcdfe6" fit="cover" />
          <div v-else style="width:80px;height:80px;border-radius:4px;border:1px dashed #dcdfe6;display:flex;align-items:center;justify-content:center;color:#c0c4cc;font-size:11px">无主图</div>
          <div>
            <el-upload :http-request="uploadMainImage" :show-file-list="false" accept="image/*">
              <el-button size="small">{{ form.main_image ? '更换主图' : '上传主图' }}</el-button>
            </el-upload>
            <div v-if="form.main_image" style="margin-top:6px">
              <el-button size="small" type="danger" text @click="form.main_image=''">移除</el-button>
            </div>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="产品图片">
        <el-upload
          list-type="picture-card"
          :http-request="uploadImage"
          :file-list="fileList"
          @remove="removeImage"
          accept="image/*"
        >
          <el-icon><Plus /></el-icon>
        </el-upload>
      </el-form-item>
      <el-form-item>
        <el-button @click="save('draft')" :loading="saving">保存草稿</el-button>
        <el-button v-if="productStatus!=='rejected'" type="primary" @click="save('submit')" :loading="saving">提交审核</el-button>
        <el-button @click="router.back()">取消</el-button>
      </el-form-item>
    </el-form>
    <div v-if="aiReviewResult" style="max-width:600px;margin-top:8px">
      <el-divider />
      <div style="font-weight:bold;margin-bottom:8px;display:flex;align-items:center;gap:8px">
        AI 审核结论
        <el-tag v-if="aiRisk==='低'" type="success" size="small">低风险</el-tag>
        <el-tag v-else-if="aiRisk==='高'" type="danger" size="small">高风险</el-tag>
        <el-tag v-else-if="aiRisk==='error'" type="danger" size="small">审核失败</el-tag>
        <el-tag v-else type="warning" size="small">中风险</el-tag>
      </div>
      <div class="ai-result-body" v-html="aiResultHtml" />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { productApi, uploadApi } from '@/api'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const isEdit = computed(() => !!route.params.id)
const productStatus = ref('')
const form = reactive({ product_name: '', product_link: '', category: '', description: '', main_image: '' })
const images = ref<string[]>([])
const fileList = ref<any[]>([])
const aiReviewResult = ref<string | null>(null)

const aiRisk = computed(() => {
  const r = aiReviewResult.value
  if (!r) return null
  if (r.startsWith('AI审核失败') || r.startsWith('无法审核')) return 'error'
  const m = r.match(/【(低|中|高)】/)
  if (m) return m[1] as '低' | '中' | '高'
  if (/高[风险度]|高度风险/.test(r)) return '高'
  if (/低[风险度]|低度风险/.test(r)) return '低'
  return '中'
})
const aiResultHtml = computed(() => aiReviewResult.value ? marked(aiReviewResult.value) as string : '')

onMounted(async () => {
  if (isEdit.value) {
    const res: any = await productApi.get(Number(route.params.id))
    const p = res.data
    Object.assign(form, { product_name: p.product_name, product_link: p.product_link || '', category: p.category || '', description: p.description || '', main_image: p.main_image || '' })
    productStatus.value = p.status
    images.value = p.images.map((img: any) => img.url)
    fileList.value = p.images.map((img: any) => ({ name: img.url, url: img.url }))
    aiReviewResult.value = p.ai_review_result || null
  }
})

async function uploadMainImage(opts: any) {
  try {
    const res: any = await uploadApi.image(opts.file)
    form.main_image = res.data.url
    opts.onSuccess({ url: res.data.url })
  } catch (e: any) {
    opts.onError(e)
    ElMessage.error('上传失败')
  }
}

async function uploadImage(opts: any) {
  try {
    const res: any = await uploadApi.image(opts.file)
    const url = res.data.url
    images.value.push(url)
    opts.onSuccess({ url })
  } catch (e: any) {
    opts.onError(e)
    ElMessage.error('上传失败')
  }
}

function removeImage(file: any) {
  const url = file.response?.url || file.url
  images.value = images.value.filter(u => u !== url)
}

async function save(action: string) {
  if (!form.product_name) return ElMessage.warning('产品名称必填')
  if (action === 'submit' && images.value.length === 0) return ElMessage.warning('提交审核需至少一张图片')
  saving.value = true
  try {
    if (isEdit.value) {
      await productApi.update(Number(route.params.id), { ...form, images: images.value })
      if (action === 'submit') await productApi.submitReview(Number(route.params.id))
    } else {
      await productApi.create({ ...form, images: images.value, action })
    }
    ElMessage.success(action === 'draft' ? '已保存草稿' : '已提交审核')
    router.push('/products')
  } catch (e: any) { ElMessage.error(e) } finally { saving.value = false }
}
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
.ai-result-body :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
.ai-result-body :deep(th),
.ai-result-body :deep(td) { border: 1px solid #dcdfe6; padding: 6px 10px; text-align: left; }
.ai-result-body :deep(th) { background: #ebeef5; font-weight: bold; white-space: nowrap; }
.ai-result-body :deep(td:first-child) { white-space: nowrap; }
.ai-result-body :deep(p) { margin: 4px 0; }
.ai-result-body :deep(strong) { font-weight: bold; }
</style>
