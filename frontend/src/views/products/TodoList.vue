<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <el-input v-model="query.keyword" placeholder="搜索产品名称" clearable style="width:160px" @change="load" />
          <el-select v-if="auth.user?.role !== 'selector'" v-model="query.creator_id" placeholder="选品员" clearable style="width:120px" @change="filterLoad">
            <el-option v-for="u in selectors" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </div>
        <div style="display:flex;gap:8px">
          <el-button v-if="auth.user?.role !== 'reviewer'" @click="bulkImportVisible=true">批量导入链接</el-button>
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
            <div style="position:relative;display:inline-block">
              <!-- 有生成图则显示生成图，否则始终显示原始图 -->
              <div v-if="row.generated_images?.no_logo" style="cursor:pointer" @click="openGenPreview(row)">
                <img :src="row.generated_images.no_logo.url" style="width:56px;height:56px;object-fit:cover;border-radius:4px" />
              </div>
              <PreviewImage v-else-if="row.main_image || row.images?.[0]?.url" :src="row.main_image || row.images[0].url" />
              <div v-else style="width:56px;height:56px;background:#f5f7fa;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#c0c4cc;font-size:11px">无图</div>
              <!-- 状态角标：不遮挡图片，仅在底部显示一条小色条 -->
              <div v-if="row.generated_images?.generating"
                   style="position:absolute;bottom:0;left:0;right:0;background:rgba(64,158,255,0.85);color:#fff;font-size:9px;text-align:center;border-radius:0 0 4px 4px;padding:1px 0">
                生成中
              </div>
              <div v-else-if="row.generated_images?.failed"
                   style="position:absolute;bottom:0;left:0;right:0;background:rgba(245,108,108,0.85);color:#fff;font-size:9px;text-align:center;border-radius:0 0 4px 4px;padding:1px 0">
                生成失败
              </div>
            </div>
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
        <el-table-column v-if="auth.user?.role !== 'selector'" label="选品员" width="100">
          <template #default="{row}">{{ row.creator?.username }}</template>
        </el-table-column>
        <el-table-column prop="approved_at" label="通过时间" width="150">
          <template #default="{row}">{{ (row.approved_at || row.updated_at)?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{row}">
            <el-button size="small" type="primary" @click="openImageGen(row)">生图</el-button>
            <el-button size="small" type="success" @click="markComplete(row)">完成</el-button>
            <el-button size="small" type="danger" @click="del(row)">删除</el-button>
            <el-button size="small" @click="router.push(`/products/${row.id}`)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" v-model:page-size="pageSize" :page-sizes="[20,50,100,200]" :total="total" @current-change="load" @size-change="onSizeChange" layout="total,sizes,prev,pager,next" />
    </el-card>

    <!-- 完成对话框 -->
    <el-dialog v-model="completeDialogVisible" title="标记完成" width="380px" @close="completeProductCode=''">
      <el-form label-width="80px">
        <el-form-item label="产品ID">
          <el-input v-model="completeProductCode" placeholder="请输入公司产品ID" clearable @keyup.enter="doMarkComplete" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="completeLoading" @click="doMarkComplete">确认完成</el-button>
      </template>
    </el-dialog>

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
      <!-- 隐藏文件输入，整框点击触发 -->
      <input ref="slotFileInput" type="file" accept="image/*" style="display:none" @change="onSlotFileChange" />
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
                 @click="previewUrl(img.url)"
                 style="width:80px;height:80px;cursor:grab;border:2px solid transparent;border-radius:4px;overflow:hidden"
                 :style="{ borderColor: isUsed(img.url) ? '#67C23A' : 'transparent' }">
              <img :src="img.url" style="width:100%;height:100%;object-fit:cover" />
            </div>
          </div>
        </div>

        <!-- 框区域 -->
        <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px">
          <!-- 变体图框 -->
          <div>
            <div style="font-size:13px;font-weight:bold;margin-bottom:8px">
              变体图（{{ slots.variant.length }}张）
              <el-button size="small" text @click="addVariantSlot">+ 加框</el-button>
              <el-button size="small" text @click="removeVariantSlot" :disabled="slots.variant.length <= 1">- 减框</el-button>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <div v-for="(v, idx) in slots.variant" :key="'var'+idx"
                   @dragover.prevent @drop="onDrop($event, 'variant', idx)"
                   style="width:80px;height:80px;border:2px dashed #dcdfe6;border-radius:4px;position:relative;overflow:hidden;cursor:pointer"
                   :style="{ borderColor: v ? '#67C23A' : '#dcdfe6' }"
                   @click="v ? previewUrl(v) : triggerSlotUpload('variant', idx)">
                <img v-if="v" :src="v" style="width:100%;height:100%;object-fit:cover" />
                <div v-else style="width:100%;height:100%;display:flex;align-items:center;justify-content:center">
                  <el-icon style="font-size:22px;color:#c0c4cc"><Plus /></el-icon>
                </div>
                <div v-if="v" @click.stop="clearSlot('variant', idx)" style="position:absolute;top:2px;right:2px;cursor:pointer;background:rgba(0,0,0,0.5);color:#fff;border-radius:50%;width:16px;height:16px;display:flex;align-items:center;justify-content:center;font-size:10px">×</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 提示词模板 -->
        <div style="margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span style="font-size:13px;font-weight:bold">无Logo提示词</span>
            <el-button size="small" text @click="templateDialogVisible=true">管理模板</el-button>
          </div>
          <el-select v-model="selectedTemplateId" placeholder="选择提示词模板" style="width:100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>

        <!-- 有Logo提示词模板 -->
        <div style="margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span style="font-size:13px;font-weight:bold">有Logo提示词</span>
          </div>
          <el-select v-model="selectedLogoTemplateId" placeholder="不选择，只生成无Logo版" clearable style="width:100%">
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
              <div v-else-if="(g.status === 'generating' || g.status === 'pending') && prevUrls[g.has_logo ? 'with_logo' : 'no_logo']"
                   style="position:relative;width:200px;height:200px;cursor:pointer" @click="previewUrl(prevUrls[g.has_logo ? 'with_logo' : 'no_logo'])">
                <img :src="prevUrls[g.has_logo ? 'with_logo' : 'no_logo']" style="width:200px;height:200px;object-fit:cover;border-radius:4px" />
                <div style="position:absolute;left:0;right:0;bottom:50%;transform:translateY(100%);padding:6px 0;background:rgba(0,0,0,0.55);color:#fff;font-size:12px;border-radius:0">
                  正在重新生成...
                </div>
              </div>
              <div v-else-if="g.status === 'generating' || g.status === 'pending'" style="width:200px;height:200px;border-radius:4px;background:linear-gradient(270deg,#409EFF,#67C23A,#E6A23C,#409EFF);background-size:600% 600%;animation:genAnim 2s ease infinite;display:flex;align-items:center;justify-content:center;color:#fff">
                生成中...
              </div>
              <div v-else-if="g.status === 'failed'" style="width:200px;height:200px;border-radius:4px;background:#fef0f0;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#F56C6C;font-size:12px;padding:8px;text-align:center;gap:6px">
                <span style="font-size:13px;font-weight:bold">生成失败</span>
                <span v-if="g.error" style="color:#909399;font-size:11px;word-break:break-all;max-height:120px;overflow-y:auto">{{ g.error }}</span>
              </div>
              <el-button size="small" style="margin-top:6px" :disabled="g.status === 'generating' || g.status === 'pending'"
                @click="regenerate(g.has_logo ? 'with_logo' : 'no_logo')">重新生成</el-button>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="genVisible=false">关闭</el-button>
        <el-button type="primary" :loading="generating" @click="doGenerate" :disabled="!selectedTemplateId">开始生图</el-button>
      </template>
    </el-dialog>

    <!-- 全屏灯箱预览 -->
    <Teleport to="body">
      <div v-if="genPreviewVisible" class="lightbox-overlay" @click.self="closeLightbox" @wheel.prevent="onPreviewWheel">
        <img :src="genPreviewImages[genPreviewIndex]" class="lightbox-img" :style="{transform:`scale(${previewScale})`}" draggable="false" @click.stop />
        <div v-if="genPreviewImages.length > 1" class="lightbox-nav">
          <el-button circle size="small" @click.stop="genPreviewIndex = (genPreviewIndex - 1 + genPreviewImages.length) % genPreviewImages.length">‹</el-button>
          <span style="color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.5);line-height:32px;font-size:13px">{{ genPreviewIndex + 1 }} / {{ genPreviewImages.length }}</span>
          <el-button circle size="small" @click.stop="genPreviewIndex = (genPreviewIndex + 1) % genPreviewImages.length">›</el-button>
        </div>
        <div class="lightbox-close" @click="closeLightbox">✕</div>
      </div>
    </Teleport>

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
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { todoApi, uploadApi, productApi, userApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import PreviewImage from '@/components/PreviewImage.vue'

const router = useRouter()
const auth = useAuthStore()
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const selected = ref<any[]>([])
const pageSize = ref(20)
const query = reactive({ page: 1, keyword: '', creator_id: undefined as number | undefined })
const selectors = ref<any[]>([])

function filterLoad() { query.page = 1; load() }

async function loadSelectors() {
  if (auth.user?.role === 'selector') return
  try {
    const res: any = await userApi.listSelectors()
    selectors.value = res.data?.items || []
  } catch {}
}

// 批量导入
const bulkImportVisible = ref(false)
const bulkUrls = ref('')
const bulkLoading = ref(false)

// 完成
const completeDialogVisible = ref(false)
const completeProductCode = ref('')
const completeLoading = ref(false)
const completeTargetRow = ref<any>(null)

// 生图
const genVisible = ref(false)
const genProduct = ref<any>(null)
const genLoading = ref(false)
const scraping = ref(false)
const generating = ref(false)
const scrapedImages = ref<any[]>([])
const genResults = ref<any[]>([])
// 重新生成时保留的旧图 url，key: no_logo / with_logo
const prevUrls = reactive<{ no_logo: string; with_logo: string }>({ no_logo: '', with_logo: '' })
const selectedTemplateId = ref<number | null>(null)
const selectedLogoTemplateId = ref<number | null>(null)
const slots = reactive({
  main: ['', ''] as string[],
  scene: [''] as string[],
  variant: ['', '', '', '', '', '', ''] as string[],
})
const slotsCache = new Map<number, string[]>() // 记住每个产品上次拖入的变体图

// 生成图预览
const genPreviewVisible = ref(false)
const genPreviewImages = ref<string[]>([])
const genPreviewIndex = ref(0)
const previewScale = ref(1)

function onPreviewWheel(e: WheelEvent) {
  previewScale.value = Math.min(10, Math.max(0.2, previewScale.value - e.deltaY * 0.002))
}

function closeLightbox() {
  genPreviewVisible.value = false
  previewScale.value = 1
}

// 隐藏文件输入
const slotFileInput = ref<HTMLInputElement | null>(null)
const currentUploadTarget = ref<{ type: 'variant'; idx: number } | null>(null)

function triggerSlotUpload(type: 'variant', idx: number) {
  currentUploadTarget.value = { type, idx }
  slotFileInput.value?.click()
}

async function onSlotFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  ;(e.target as HTMLInputElement).value = ''
  if (!file || !currentUploadTarget.value) return
  const { idx } = currentUploadTarget.value
  try {
    const res: any = await uploadApi.image(file)
    const url = res.data.url
    slots.variant[idx] = url
  } catch (err: any) {
    ElMessage.error(err || '上传失败')
  }
}

function isModelError(err: string | null | undefined) {
  if (!err) return false
  const lower = err.toLowerCase()
  return lower.includes('model') || lower.includes('api') || lower.includes('openai') || lower.includes('connect') || lower.includes('timeout') || lower.includes('key')
}

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

async function silentRefresh(force = false) {
  // 有对话框打开时跳过，不打断用户操作（除非强制刷新）
  if (!force && (genVisible.value || bulkImportVisible.value || templateDialogVisible.value || templateEditVisible.value || completeDialogVisible.value)) return
  try {
    const res: any = await todoApi.list({ ...query, page_size: pageSize.value })
    // 数据没变化就不替换，避免不必要的重渲染和闪屏
    const incoming = JSON.stringify(res.data.items)
    if (incoming !== JSON.stringify(list.value)) {
      const _map = new Map(list.value.map((r: any) => [r.id, r]))
      list.value = res.data.items.map((row: any) => {
        const ex = _map.get(row.id)
        if (ex) { Object.assign(ex, row); return ex }
        return row
      })
      total.value = res.data.total
    }
  } catch {} // 后台静默失败，不弹错误
}

async function del(row: any) {
  await ElMessageBox.confirm('确认彻底删除该产品？此操作不可恢复。', '删除确认', { type: 'warning' })
  try {
    await productApi.delete(row.id)
    ElMessage.success('已删除')
    load()
  } catch (e: any) { ElMessage.error(e || '删除失败') }
}

async function markComplete(row: any) {
  completeTargetRow.value = row
  completeProductCode.value = ''
  completeDialogVisible.value = true
}

async function doMarkComplete() {
  if (!completeProductCode.value.trim()) return ElMessage.warning('请输入产品ID')
  completeLoading.value = true
  try {
    await todoApi.complete(completeTargetRow.value.id, completeProductCode.value.trim())
    ElMessage.success('已标记完成')
    completeDialogVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e || '操作失败') }
  finally { completeLoading.value = false }
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

function previewUrl(url: string) {
  genPreviewImages.value = [url]
  genPreviewIndex.value = 0
  previewScale.value = 1
  genPreviewVisible.value = true
}

// 生图弹窗
async function saveSlotCache() {
  if (genProduct.value?.id != null) {
    slotsCache.set(genProduct.value.id, [...slots.variant])
    try {
      await todoApi.saveSlots(genProduct.value.id, slots.variant)
    } catch {}
  }
}

async function openImageGen(row: any) {
  genProduct.value = row
  genVisible.value = true
  genLoading.value = true
  scrapedImages.value = []
  genResults.value = []
  prevUrls.no_logo = ''
  prevUrls.with_logo = ''
  selectedLogoTemplateId.value = null
  slots.variant = slotsCache.has(row.id)
    ? [...slotsCache.get(row.id)!]
    : ['', '', '', '', '', '', '']

  try {
    const matRes: any = await todoApi.getMaterials(row.id)
    if (matRes.data?.length) {
      // 素材池只显示爬取的图片
      scrapedImages.value = matRes.data.filter((m: any) => m.type === 'scraped').map((m: any) => ({ url: m.url, id: m.id }))

      // 没有内存缓存时，从后端恢复变体槽位
      if (!slotsCache.has(row.id)) {
        const variantMats = matRes.data
          .filter((m: any) => m.type === 'variant')
          .sort((a: any, b: any) => a.sort_order - b.sort_order)
        if (variantMats.length > 0) {
          const maxIdx = Math.max(...variantMats.map((m: any) => m.sort_order))
          slots.variant = Array(Math.max(maxIdx + 1, 7)).fill('')
          variantMats.forEach((m: any) => { slots.variant[m.sort_order] = m.url })
        }
      }
    }

    const genRes: any = await todoApi.getGenerated(row.id)
    genResults.value = genRes.data || []
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

function onDrop(e: DragEvent, type: 'variant', idx: number) {
  const url = e.dataTransfer?.getData('text/plain')
  if (!url) return
  slots.variant[idx] = url
}

function clearSlot(type: 'variant', idx: number) {
  slots.variant[idx] = ''
}

function addVariantSlot() {
  slots.variant.push('')
}

function removeVariantSlot() {
  if (slots.variant.length <= 1) return
  // 优先删最后一个空框，没有空框则删最后一个
  const lastEmptyIdx = slots.variant.lastIndexOf('')
  if (lastEmptyIdx >= 0) {
    slots.variant.splice(lastEmptyIdx, 1)
  } else {
    slots.variant.pop()
  }
}

function isUsed(url: string) {
  return slots.variant.includes(url)
}

// 生图
async function doGenerate() {
  if (!selectedTemplateId.value) return ElMessage.warning('请选择提示词模板')
  if (!genProduct.value) return

  if (!slots.variant.some(Boolean)) return ElMessage.warning('请至少拖入一张素材')

  // 先保存当前槽位到后端，再生图
  await saveSlotCache()

  // 开始生图前保留旧图（如已有），重新生成期间继续显示
  prevUrls.no_logo = genResults.value.find((g: any) => !g.has_logo && g.status === 'done')?.url || ''
  prevUrls.with_logo = genResults.value.find((g: any) => g.has_logo && g.status === 'done')?.url || ''
  generating.value = true
  try {
    const mode = selectedLogoTemplateId.value ? 'both' : 'no_logo'
    await todoApi.generate(genProduct.value.id, selectedTemplateId.value, mode, selectedLogoTemplateId.value ?? undefined)
    pollGenStatus()
  } catch (e: any) {
    const msg = typeof e === 'string' ? e : ''
    if (msg.includes('API Key') || msg.includes('未配置') || msg.includes('api_key')) {
      ElMessage.error('请配置模型（系统设置 → AI 生图设置）')
    } else {
      ElMessage.error('生成失败')
    }
  } finally { generating.value = false }
}

// 单独重新生成某一版，旧图保留显示
async function regenerate(mode: 'no_logo' | 'with_logo') {
  if (!selectedTemplateId.value) return ElMessage.warning('请选择提示词模板')
  if (!genProduct.value) return
  if (!slots.variant.some(Boolean)) return ElMessage.warning('请至少拖入一张素材')

  await saveSlotCache()

  // 记住旧图，重新生成期间继续显示
  const old = genResults.value.find((g: any) => (mode === 'with_logo') === !!g.has_logo)
  prevUrls[mode] = old?.status === 'done' && old?.url ? old.url : ''

  try {
    await todoApi.generate(genProduct.value.id, selectedTemplateId.value, mode, selectedLogoTemplateId.value ?? undefined)
    pollGenStatus()
  } catch (e: any) {
    prevUrls[mode] = ''
    const msg = typeof e === 'string' ? e : ''
    if (msg.includes('API Key') || msg.includes('未配置') || msg.includes('api_key')) {
      ElMessage.error('请配置模型（系统设置 → AI 生图设置）')
    } else {
      ElMessage.error('生成失败')
    }
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
function pollGenStatus() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!genProduct.value) return
    const res: any = await todoApi.getGenerated(genProduct.value.id)
    genResults.value = (res.data || []).sort((a: any, b: any) => (a.has_logo ? 1 : 0) - (b.has_logo ? 1 : 0))
    const allDone = genResults.value.length > 0 && genResults.value.every((g: any) => g.status === 'done' || g.status === 'failed')
    if (allDone && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
      prevUrls.no_logo = ''
      prevUrls.with_logo = ''
      silentRefresh(true) // 强制静默刷新列表，更新主图缩略图和失败状态
      // 根据结果给出提示
      const hasDone = genResults.value.some((g: any) => g.status === 'done')
      const allFailed = genResults.value.every((g: any) => g.status === 'failed')
      if (allFailed) {
        const firstError = genResults.value[0]?.error || ''
        if (isModelError(firstError)) {
          ElMessage.error('请配置模型（系统设置 → AI 生图设置）')
        } else {
          ElMessage.error('生成失败')
        }
      } else if (hasDone) {
        ElMessage.success('生图完成')
      }
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

// 监听对话框关闭，自动保存变体框缓存
watch(genVisible, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    saveSlotCache()
  }
})

let _timer: ReturnType<typeof setInterval>
watch([() => query.page, pageSize, () => query.creator_id], () => {
  sessionStorage.setItem('pag:todo', JSON.stringify({ page: query.page, pageSize: pageSize.value, creator_id: query.creator_id }))
})
onMounted(() => {
  const saved = sessionStorage.getItem('pag:todo')
  if (saved) {
    const p = JSON.parse(saved)
    query.page = p.page; pageSize.value = p.pageSize
    query.creator_id = p.creator_id ?? undefined
  }
  load(); loadSelectors(); _timer = setInterval(silentRefresh, 15000)
})
onUnmounted(() => { clearInterval(_timer); if (pollTimer) clearInterval(pollTimer) })
</script>

<style>
@keyframes genAnim {
  0% { background-position: 0% 50% }
  50% { background-position: 100% 50% }
  100% { background-position: 0% 50% }
}
.lightbox-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  z-index: 9999;
  background: rgba(0,0,0,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
  user-select: none;
}
.lightbox-img {
  max-width: 95vw;
  max-height: 95vh;
  transition: transform 0.1s;
  transform-origin: center;
  cursor: default;
}
.lightbox-nav {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  z-index: 10000;
}
.lightbox-close {
  position: absolute;
  top: 20px;
  right: 28px;
  color: #fff;
  font-size: 28px;
  cursor: pointer;
  z-index: 10000;
  opacity: 0.7;
  transition: opacity 0.2s;
}
.lightbox-close:hover { opacity: 1; }
</style>
