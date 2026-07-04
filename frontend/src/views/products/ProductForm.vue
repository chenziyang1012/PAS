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
      <el-form-item label="产品图片" required>
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
        <el-button type="primary" @click="save('submit')" :loading="saving">提交审核</el-button>
        <el-button @click="router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { productApi, uploadApi } from '@/api'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const isEdit = computed(() => !!route.params.id)
const form = reactive({ product_name: '', product_link: '', category: '', description: '' })
const images = ref<string[]>([])
const fileList = ref<any[]>([])

onMounted(async () => {
  if (isEdit.value) {
    const res: any = await productApi.get(Number(route.params.id))
    const p = res.data
    Object.assign(form, { product_name: p.product_name, product_link: p.product_link || '', category: p.category || '', description: p.description || '' })
    images.value = p.images.map((img: any) => img.url)
    fileList.value = p.images.map((img: any) => ({ name: img.url, url: img.url }))
  }
})

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
