<template>
  <div>
    <el-card>
      <template #header><span style="font-weight:bold">系统设置</span></template>

      <h3 style="margin-bottom:16px">我的 1688 Cookie</h3>
      <el-alert type="info" :closable="false" style="margin-bottom:16px">
        <p>每个用户需要配置自己的 1688 Cookie，使用自己的1688账号登录后获取。这样多人同时操作不会互相影响。</p>
        <ol style="margin:8px 0 0 16px;line-height:2">
          <li>用浏览器打开 <el-link href="https://www.1688.com" target="_blank" type="primary">1688.com</el-link> 并登录你自己的账号</li>
          <li>按 F12 打开开发者工具，切换到 "Network（网络）" 标签</li>
          <li>刷新页面，点击任意一个请求</li>
          <li>在 "Headers（请求头）" 中找到 <b>Cookie</b> 字段，复制完整内容</li>
          <li>粘贴到下方输入框中并保存</li>
        </ol>
      </el-alert>

      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
        <span>当前状态：</span>
        <el-tag v-if="myCookieConfigured" type="success">已配置</el-tag>
        <el-tag v-else type="danger">未配置</el-tag>
      </div>

      <el-input v-model="myCookieValue" type="textarea" :rows="4" placeholder="粘贴从浏览器复制的 Cookie 字符串..." />
      <div style="margin-top:12px">
        <el-button type="primary" :loading="savingMy" @click="saveMyCookie">保存我的 Cookie</el-button>
        <el-button @click="testMyCookie" :loading="testingMy">测试爬取</el-button>
        <el-button v-if="myCookieConfigured" type="danger" :loading="deletingMy" @click="deleteMyCookie">删除 Cookie</el-button>
      </div>

      <div v-if="testResult" style="margin-top:16px">
        <el-divider>测试结果</el-divider>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="产品名称">{{ testResult.title || '未获取到' }}</el-descriptions-item>
          <el-descriptions-item label="主图">
            <el-image v-if="testResult.image" :src="testResult.image" style="width:100px;height:100px" fit="cover" />
            <span v-else>未获取到</span>
          </el-descriptions-item>
          <el-descriptions-item label="厂家名称">{{ testResult.manufacturer || '未获取到' }}</el-descriptions-item>
          <el-descriptions-item v-if="testResult.error" label="错误"><el-text type="danger">{{ testResult.error }}</el-text></el-descriptions-item>
        </el-descriptions>
      </div>

      <template v-if="auth.user?.role === 'admin'">
        <el-divider />
        <h3 style="margin-bottom:16px">全局默认 Cookie（管理员）</h3>
        <el-alert type="warning" :closable="false" style="margin-bottom:16px">
          <p>当用户未配置自己的 Cookie 时，系统将使用此全局 Cookie 作为兜底。建议每个用户配置自己的 Cookie。</p>
        </el-alert>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
          <span>全局状态：</span>
          <el-tag v-if="globalConfigured" type="success">已配置</el-tag>
          <el-tag v-else type="danger">未配置</el-tag>
        </div>
        <el-input v-model="globalCookieValue" type="textarea" :rows="4" placeholder="粘贴全局默认 Cookie..." />
        <div style="margin-top:12px">
          <el-button type="primary" :loading="savingGlobal" @click="saveGlobalCookie">保存全局 Cookie</el-button>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { productApi } from '@/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const myCookieValue = ref('')
const myCookieConfigured = ref(false)
const savingMy = ref(false)
const deletingMy = ref(false)
const testingMy = ref(false)
const testResult = ref<any>(null)

const globalCookieValue = ref('')
const globalConfigured = ref(false)
const savingGlobal = ref(false)

async function loadStatus() {
  try {
    const res: any = await productApi.getMyCookie1688()
    myCookieConfigured.value = res.data.configured
  } catch {}
  if (auth.user?.role === 'admin') {
    try {
      const res: any = await productApi.getCookie1688()
      globalConfigured.value = res.data.configured
    } catch {}
  }
}

async function saveMyCookie() {
  if (!myCookieValue.value.trim()) return ElMessage.warning('请输入 Cookie')
  savingMy.value = true
  try {
    await productApi.setMyCookie1688(myCookieValue.value.trim())
    ElMessage.success('Cookie 已保存')
    myCookieConfigured.value = true
    myCookieValue.value = ''
  } catch (e: any) {
    ElMessage.error(e || '保存失败')
  } finally {
    savingMy.value = false
  }
}

async function deleteMyCookie() {
  deletingMy.value = true
  try {
    await productApi.deleteMyCookie1688()
    ElMessage.success('Cookie 已删除')
    myCookieConfigured.value = false
  } catch (e: any) {
    ElMessage.error(e || '删除失败')
  } finally {
    deletingMy.value = false
  }
}

async function testMyCookie() {
  testingMy.value = true
  testResult.value = null
  try {
    const res: any = await productApi.scrape('https://detail.1688.com/offer/622463490498.html')
    testResult.value = res.data
  } catch (e: any) {
    ElMessage.error(e || '测试失败')
  } finally {
    testingMy.value = false
  }
}

async function saveGlobalCookie() {
  if (!globalCookieValue.value.trim()) return ElMessage.warning('请输入 Cookie')
  savingGlobal.value = true
  try {
    await productApi.setCookie1688(globalCookieValue.value.trim())
    ElMessage.success('全局 Cookie 已保存')
    globalConfigured.value = true
    globalCookieValue.value = ''
  } catch (e: any) {
    ElMessage.error(e || '保存失败')
  } finally {
    savingGlobal.value = false
  }
}

onMounted(loadStatus)
</script>
