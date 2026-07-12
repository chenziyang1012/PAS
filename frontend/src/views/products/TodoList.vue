<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-input v-model="query.keyword" placeholder="搜索产品名称" clearable style="width:160px" @change="load" />
        </div>
        <div style="display:flex;gap:8px">
          <el-button @click="bulkImportVisible=true">批量导入链接</el-button>
        </div>
      </div>

      <div v-if="selected.length" style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span style="color:#606266">已选 {{ selected.length }} 项</span>
        <el-button size="small" type="success" @click="batchComplete">批量标记完成</el-button>
      </div>

      <el-table :data="list" v-loading="loading" @selection-change="selected=$event">
        <el-table-column type="selection" width="45" />
        <el-table-column label="主图" width="130">
          <template #default="{row}">
            <div v-if="row.generated_images?.generating" style="width:56px;height:56px;border-radius:4px;background:linear-gradient(270deg,#409EFF,#67C23A,#E6A23C,#409EFF);background-size:600% 600%;animation:genAnim 2s ease infinite;display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px">
              生成中...
            </div>
            <div v-else-if="row.generated_images?.no_logo" style="display:inline-block;cursor:pointer" @click="openGenPreview(row)">
              <img :src="row.generated_images.no_logo.url" style="width:56px;height:56px;object-fit:cover;border-radius:4px" />
            </div>
            <PreviewImage v-else-if="row.main_image || row.images?.[0]?.url" :src="row.main_image || row.images[0].url" />
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
        <el-table-column label="选品员" width="100">
          <template #default="{row}">{{ row.creator?.username }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="通过时间" width="150">
          <template #default="{row}">{{ row.updated_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{row}">
            <el-button size="small" type="primary" @click="openImageGen(row)">生图</el-button>
            <el-button size="small" type="success" @click="markComplete(row)">完成</el-button>
            <el-button size="small" @click="router.push(`/products/${row.id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" v-model:page-size="pageSize" :page-sizes="[20,50,100,200]" :total="total" @current-change="load" @size-change="onSizeChange" layout="total,sizes,prev,pager,next" />
    </el-card>

    <!-- 批量导入 -->
    <el-dialog v-model="bulkImportVisible" title="批量导入产品链接（待做）" width="500px">
      <p style="color:#606266;font-size:13px;margin-bottom:8px">每行输入一个产品链接，导入后直接进入待做列表</p>
      <div style="margin-bottom:8px;display:flex;gap:8px">
        <el-upload :show-file-list="false" accept=".txt" :auto-upload="false" @change="handleTxtChange">
          <el-button size="small">上传 .txt 文件</el-button>
        </el-upload>
        <el-upload :show-file-list="false" accept=".xlsx,.xls" :auto-upload="false" @change="handleExcelChange">
          <el-button size="small">上传 Excel 文件</el-button>
        </el-upload>
      </div>
      <el-input v-model="bulkUrls" type="textarea" :rows="8" placeholder="https://..." />
      <template #footer>
        <el-button @click="bulkImportVisible=false">取消</el-button>
        <el-button type="primary" :loading="bulkLoading" @click="doBulkImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- 生图弹窗 -->
    <el-dialog v-model="genVisible" :title="`生图 - ${genProduct?.product_name || ''}`" width="900px" top="5vh" destroy-on-close>
      <div v-loading="genLoading">
        <!-- 素材区 -->
        <div style="margin-bottom:16px;display:flex;justify-content:space-between;align-items:center">
          <h4 style="margin:0">素材图片</h4>
          <el-button type="primary" size="small" :loading="scraping" @click="scrapeMaterials">从1688爬取素材</el-button>
        </div>

        <!-- 素材池 -->
        <div v-if="scrapedImages.length" style="margin-bottom:16px">
          <div style="font-size:13px;color:#909399;margin-bottom:8px">素材池（拖拽到下方框中）</div>
          <div style="display:flex;flex-wrap:wrap;gap:8px;max-height:200px;overflow-y:auto;padding:8px;background:#f5f7fa;border-radius:4px">
            <div v-for="(img, i) in scrapedImages" :key="i"
                 draggable="true" @dragstart="onDragStart($event, img.url)"
                 style="width:80px;height:80px;cursor:grab;border:2px solid transparent;border-radius:4px;overflow:hidden"
                 :style="{ borderColor: isUsed(img.url) ? '#67C23A' : 'transparent' }">
              <img :src="img.url" style="width:100%;height:100%;object-fit:cover" />
            </div>
          </div>
        </div>

        <!-- 框区域 -->
        <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px">
          <!-- 主视图框 x2 -->
          <div>
            <div style="font-size:13px;font-weight:bold;margin-bottom:8px">主视图（2张）</div>
            <div style="display:flex;gap:8px">
              <div v-for="idx in 2" :key="'main'+idx"
                   @dragover.prevent @drop="onDrop($event, 'main', idx-1)"
                   style="width:100px;height:100px;border:2px dashed #dcdfe6;border-radius:4px;display:flex;align-items:center;justify-content:center;position:relative"
                   :style="{ borderColor: slots.main[idx-1] ? '#409EFF' : '#dcdfe6' }">
                <img v-if="slots.main[idx-1]" :src="slots.main[idx-1]" style="width:100%;height:100%;object-fit:cover;border-radius:2px" />
                <span v-else style="color:#c0c4cc;font-size:12px">拖入</span>
                <div v-if="slots.main[idx-1]" @click="clearSlot('main', idx-1)" style="position:absolute;top:2px;right:2px;cursor:pointer;background:rgba(0,0,0,0.5);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:12px">×</div>
              </div>
            </div>
          </div>

          <!-- 场景图框 x1 -->
          <div>
            <div style="font-size:13px;font-weight:bold;margin-bottom:8px">场景图（1张）</div>
            <div @dragover.prevent @drop="onDrop($event, 'scene', 0)"
                 style="width:100px;height:100px;border:2px dashed #dcdfe6;border-radius:4px;display:flex;align-items:center;justify-content:center;position:relative"
                 :style="{ borderColor: slots.scene[0] ? '#E6A23C' : '#dcdfe6' }">
              <img v-if="slots.scene[0]" :src="slots.scene[0]" style="width:100%;height:100%;object-fit:cover;border-radius:2px" />
              <span v-else style="color:#c0c4cc;font-size:12px">拖入</span>
              <div v-if="slots.scene[0]" @click="clearSlot('scene', 0)" style="position:absolute;top:2px;right:2px;cursor:pointer;background:rgba(0,0,0,0.5);color:#fff;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;font-size:12px">×</div>
            </div>
          </div>

          <!-- 变体图框 -->
          <div>
            <div style="font-size:13px;font-weight:bold;margin-bottom:8px">
              变体图（{{ slots.variant.length }}张）
              <el-button size="small" text @click="addVariantSlot">+ 加框</el-button>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <div v-for="(v, idx) in slots.variant" :key="'var'+idx"
                   @dragover.prevent @drop="onDrop($event, 'variant', idx)"
                   style="width:80px;height:80px;border:2px dashed #dcdfe6;border-radius:4px;display:flex;align-items:center;justify-content:center;position:relative"
                   :style="{ borderColor: v ? '#67C23A' : '#dcdfe6' }">
                <img v-if="v" :src="v" style="width:100%;height:100%;object-fit:cover;border-radius:2px" />
                <span v-else style="color:#c0c4cc;font-size:11px">拖入</span>
                <div v-if="v" @click="clearSlot('variant', idx)" style="position:absolute;top:2px;right:2px;cursor:pointer;background:rgba(0,0,0,0.5);color:#fff;border-radius:50%;width:16px;height:16px;display:flex;align-items:center;justify-content:center;font-size:10px">×</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 提示词模板 -->
        <div style="margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span style="font-size:13px;font-weight:bold">提示词模板</span>
            <el-button size="small" text @click="templateDialogVisible=true">管理模板</el-button>
          </div>
          <el-select v-model="selectedTemplateId" placeholder="选择提示词模板" style="width:100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>

        <!-- 生成结果 -->
        <div v-if="genResults.length" style="margin-bottom:16px">
          <div style="font-size:13px;font-weight:bold;margin-bottom:8px">生成结果</div>
          <div style="display:flex;gap:16px">
            <div v-for="g in genResults" :key="g.id" style="text-align:center">
              <div style="font-size:12px;color:#909399;margin-bottom:4px">{{ g.has_logo ? '有Logo版' : '无Logo版' }}</div>
              <div v-if="g.status === 'done'" style="cursor:pointer" @click="previewGenImage(g)">
                <img :src="g.url" style="width:200px;height:200px;object-fit:cover;border-radius:4px" />
              </div>
              <div v-else-if="g.status === 'generating' || g.status === 'pending'" style="width:200px;height:200px;border-radius:4px;background:linear-gradient(270deg,#409EFF,#67C23A,#E6A23C,#409EFF);background-size:600% 600%;animation:genAnim 2s ease infinite;display:flex;align-items:center;justify-content:center;color:#fff">
                生成中...
              </div>
              <div v-else-if="g.status === 'failed'" style="width:200px;height:200px;border-radius:4px;background:#fef0f0;display:flex;align-items:center;justify-content:center;color:#F56C6C;font-size:12px;padding:8px">
                {{ g.error || '生成失败' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="genVisible=false">关闭</el-button>
        <el-button type="primary" :loading="generating" @click="doGenerate" :disabled="!selectedTemplateId">开始生图</el-button>
      </template>
    </el-dialog>

    <!-- 生成图预览(轮播) -->
    <el-dialog v-model="genPreviewVisible" :show-header="false" width="fit-content" :close-on-click-modal="true" append-to-body center>
      <div style="position:relative;display:inline-block">
        <img :src="genPreviewImages[genPreviewIndex]" style="max-width:90vw;max-height:85vh;display:block" />
        <div v-if="genPreviewImages.length > 1" style="position:absolute;bottom:16px;left:50%;transform:translateX(-50%);display:flex;gap:8px">
          <el-button circle size="small" @click="genPreviewIndex = (genPreviewIndex - 1 + genPreviewImages.length) % genPreviewImages.length">‹</el-button>
          <span style="color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.5);line-height:32px;font-size:13px">{{ genPreviewIndex + 1 }} / {{ genPreviewImages.length }}</span>
          <el-button circle size="small" @click="genPreviewIndex = (genPreviewIndex + 1) % genPreviewImages.length">›</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 模板管理 -->
    <el-dialog v-model="templateDialogVisible" title="提示词模板管理" width="600px">
      <div style="margin-bottom:12px">
        <el-button type="primary" size="small" @click="newTemplate">新建模板</el-button>
      </div>
      <el-table :data="templates" size="small">
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="content" label="内容" show-overflow-tooltip />
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-button size="small" text @click="editTemplate(row)">编辑</el-button>
            <el-button size="small" text type="danger" @click="delTemplate(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 新建/编辑模板 -->
    <el-dialog v-model="templateEditVisible" :title="templateForm.id ? '编辑模板' : '新建模板'" width="500px">
      <el-form label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="templateForm.name" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="templateForm.content" type="textarea" :rows="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="templateEditVisible=false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as XLSX from 'xlsx'
import { todoApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PreviewImage from '@/components/PreviewImage.vue'

const router = useRouter()
const auth = useAuthStore()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const selected = ref<any[]>([])
const pageSize = ref(20)
const query = reactive({ page: 1, keyword: '' })

// 批量导入
const bulkImportVisible = ref(false)
const bulkUrls = ref('')
const bulkLoading = ref(false)

// 生图
const genVisible = ref(false)
const genProduct = ref<any>(null)
const genLoading = ref(false)
const scraping = ref(false)
const generating = ref(false)
const scrapedImages = ref<any[]>([])
const genResults = ref<any[]>([])
const selectedTemplateId = ref<number | null>(null)
const slots = reactive({
  main: ['', ''] as string[],
  scene: [''] as string[],
  variant: ['', '', '', '', '', '', ''] as string[],
})

// 生成图预览
const genPreviewVisible = ref(false)
const genPreviewImages = ref<string[]>([])
const genPreviewIndex = ref(0)

// 模板
const templates = ref<any[]>([])
const templateDialogVisible = ref(false)
const templateEditVisible = ref(false)
const templateForm = reactive({ id: 0, name: '', content: '' })

function onSizeChange() { query.page = 1; load() }

async function load() {
  loading.value = true
  try {
    const res: any = await todoApi.list({ ...query, page_size: pageSize.value })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

async function markComplete(row: any) {
  await ElMessageBox.confirm('确认标记完成？完成后将进入已做列表。')
  try {
    await todoApi.complete(row.id)
    ElMessage.success('已标记完成')
    load()
  } catch (e: any) { ElMessage.error(e || '操作失败') }
}

async function batchComplete() {
  await ElMessageBox.confirm(`确认将 ${selected.value.length} 个产品标记完成？`)
  const ids = selected.value.map((r: any) => r.id)
  try {
    await todoApi.batchComplete(ids)
    ElMessage.success('批量标记完成')
    load()
  } catch (e: any) { ElMessage.error(e || '操作失败') }
}

// 批量导入
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
        if (val.startsWith('http://') || val.startsWith('https://')) urls.push(val)
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
    const res: any = await todoApi.bulkCreate(urls)
    ElMessage.success(`成功导入 ${res.data.created} 个产品`)
    bulkImportVisible.value = false
    bulkUrls.value = ''
    load()
  } catch (e: any) { ElMessage.error(e || '导入失败') }
  finally { bulkLoading.value = false }
}

// 生图弹窗
async function openImageGen(row: any) {
  genProduct.value = row
  genVisible.value = true
  genLoading.value = true
  scrapedImages.value = []
  genResults.value = []
  slots.main = ['', '']
  slots.scene = ['']
  slots.variant = ['', '', '', '', '', '', '']
  try {
    // 加载已有素材
    const matRes: any = await todoApi.getMaterials(row.id)
    if (matRes.data?.length) {
      scrapedImages.value = matRes.data.map((m: any) => ({ url: m.url, type: m.type, id: m.id }))
      // 恢复已分配的素材到框
      for (const m of matRes.data) {
        if (m.type === 'main') {
          const idx = slots.main.indexOf('')
          if (idx >= 0) slots.main[idx] = m.url
        } else if (m.type === 'scene') {
          if (!slots.scene[0]) slots.scene[0] = m.url
        } else if (m.type === 'variant') {
          const idx = slots.variant.indexOf('')
          if (idx >= 0) slots.variant[idx] = m.url
        }
      }
    }
    // 加载生成结果
    const genRes: any = await todoApi.getGenerated(row.id)
    genResults.value = genRes.data || []
    // 加载模板
    await loadTemplates()
  } finally { genLoading.value = false }
}

async function scrapeMaterials() {
  if (!genProduct.value) return
  scraping.value = true
  try {
    const res: any = await todoApi.scrapeMaterials(genProduct.value.id)
    scrapedImages.value = (res.data.urls || []).map((url: string) => ({ url }))
    ElMessage.success(`获取到 ${res.data.count} 张素材`)
  } catch (e: any) { ElMessage.error(e || '爬取失败') }
  finally { scraping.value = false }
}

// 拖拽
function onDragStart(e: DragEvent, url: string) {
  e.dataTransfer?.setData('text/plain', url)
}

function onDrop(e: DragEvent, type: 'main' | 'scene' | 'variant', idx: number) {
  const url = e.dataTransfer?.getData('text/plain')
  if (!url) return
  if (type === 'main') slots.main[idx] = url
  else if (type === 'scene') slots.scene[idx] = url
  else slots.variant[idx] = url
}

function clearSlot(type: 'main' | 'scene' | 'variant', idx: number) {
  if (type === 'main') slots.main[idx] = ''
  else if (type === 'scene') slots.scene[idx] = ''
  else slots.variant[idx] = ''
}

function addVariantSlot() {
  slots.variant.push('')
}

function isUsed(url: string) {
  return slots.main.includes(url) || slots.scene.includes(url) || slots.variant.includes(url)
}

// 生图
async function doGenerate() {
  if (!selectedTemplateId.value) return ElMessage.warning('请选择提示词模板')
  if (!genProduct.value) return

  // 保存素材分配
  const items: any[] = []
  slots.main.filter(Boolean).forEach((url, i) => items.push({ url, type: 'main', sort_order: i }))
  slots.scene.filter(Boolean).forEach((url, i) => items.push({ url, type: 'scene', sort_order: i }))
  slots.variant.filter(Boolean).forEach((url, i) => items.push({ url, type: 'variant', sort_order: i }))

  if (!items.length) return ElMessage.warning('请至少拖入一张素材')

  // 先清除旧素材再添加新的
  for (const item of items) {
    await todoApi.addMaterial(genProduct.value.id, item)
  }

  generating.value = true
  try {
    await todoApi.generate(genProduct.value.id, selectedTemplateId.value)
    ElMessage.success('已开始生成，请等待...')
    // 轮询状态
    pollGenStatus()
  } catch (e: any) { ElMessage.error(e || '生成失败') }
  finally { generating.value = false }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
function pollGenStatus() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!genProduct.value) return
    const res: any = await todoApi.getGenerated(genProduct.value.id)
    genResults.value = res.data || []
    const allDone = genResults.value.every((g: any) => g.status === 'done' || g.status === 'failed')
    if (allDone && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      load() // 刷新列表更新主图
    }
  }, 3000)
}

// 生成图预览(轮播)
function openGenPreview(row: any) {
  const imgs: string[] = []
  if (row.generated_images?.no_logo?.url) imgs.push(row.generated_images.no_logo.url)
  if (row.generated_images?.with_logo?.url) imgs.push(row.generated_images.with_logo.url)
  if (imgs.length) {
    genPreviewImages.value = imgs
    genPreviewIndex.value = 0
    genPreviewVisible.value = true
  }
}

function previewGenImage(g: any) {
  // 在生图弹窗内预览单张
  const imgs: string[] = []
  for (const r of genResults.value) {
    if (r.url) imgs.push(r.url)
  }
  genPreviewImages.value = imgs
  genPreviewIndex.value = imgs.indexOf(g.url) >= 0 ? imgs.indexOf(g.url) : 0
  genPreviewVisible.value = true
}

// 模板管理
async function loadTemplates() {
  try {
    const res: any = await todoApi.listTemplates()
    templates.value = res.data || []
    if (templates.value.length && !selectedTemplateId.value) {
      const def = templates.value.find((t: any) => t.is_default)
      selectedTemplateId.value = def ? def.id : templates.value[0].id
    }
  } catch {}
}

function newTemplate() {
  templateForm.id = 0
  templateForm.name = ''
  templateForm.content = ''
  templateEditVisible.value = true
}

function editTemplate(row: any) {
  templateForm.id = row.id
  templateForm.name = row.name
  templateForm.content = row.content
  templateEditVisible.value = true
}

async function saveTemplate() {
  if (!templateForm.name.trim() || !templateForm.content.trim()) return ElMessage.warning('名称和内容必填')
  try {
    if (templateForm.id) {
      await todoApi.updateTemplate(templateForm.id, { name: templateForm.name, content: templateForm.content })
    } else {
      await todoApi.createTemplate({ name: templateForm.name, content: templateForm.content })
    }
    ElMessage.success('保存成功')
    templateEditVisible.value = false
    await loadTemplates()
  } catch (e: any) { ElMessage.error(e || '保存失败') }
}

async function delTemplate(row: any) {
  await ElMessageBox.confirm('确认删除该模板？')
  try {
    await todoApi.deleteTemplate(row.id)
    ElMessage.success('已删除')
    await loadTemplates()
  } catch (e: any) { ElMessage.error(e || '删除失败') }
}

let _timer: ReturnType<typeof setInterval>
onMounted(() => { load(); _timer = setInterval(load, 15000) })
onUnmounted(() => { clearInterval(_timer); if (pollTimer) clearInterval(pollTimer) })
</script>

<style>
@keyframes genAnim {
  0% { background-position: 0% 50% }
  50% { background-position: 100% 50% }
  100% { background-position: 0% 50% }
}
.el-dialog .el-dialog__body:has(> div > img) { padding: 0; line-height: 0; }
</style>
