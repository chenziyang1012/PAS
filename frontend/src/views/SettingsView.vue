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
        <h3 style="margin-bottom:16px">代理设置（管理员）</h3>
        <el-alert type="info" :closable="false" style="margin-bottom:16px">
          <p>配置 HTTP 代理用于爬取 1688 等网站。阿里云服务器 IP 可能被 1688 封禁，通过代理可以绕过限制。</p>
          <p style="margin-top:4px">格式示例：<code>http://用户名:密码@代理地址:端口</code> 或 <code>http://代理地址:端口</code></p>
        </el-alert>
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
          <span>代理状态：</span>
          <el-tag v-if="proxyConfigured" type="success">已配置</el-tag>
          <el-tag v-else type="info">未配置</el-tag>
        </div>
        <el-input v-model="proxyValue" placeholder="http://user:pass@host:port" style="max-width:500px" />
        <div style="margin-top:12px">
          <el-button type="primary" :loading="savingProxy" @click="saveProxy">保存代理</el-button>
          <el-button v-if="proxyConfigured" type="danger" :loading="deletingProxy" @click="deleteProxy">删除代理</el-button>
          <el-button @click="testProxy" :loading="testingProxy">测试代理</el-button>
        </div>
        <div v-if="proxyTestResult" style="margin-top:12px">
          <el-alert :type="proxyTestResult.ok ? 'success' : 'error'" :closable="false">
            {{ proxyTestResult.msg }}
          </el-alert>
        </div>
      </template>

      <template v-if="auth.user?.role === 'admin'">
        <el-divider />
        <h3 style="margin-bottom:16px">AI 生图设置（管理员）</h3>
        <el-alert type="info" :closable="false" style="margin-bottom:16px">
          <p>配置用于生成产品图片的 OpenAI 兼容接口。API Key 和接口地址将用于待做列表的生图功能。</p>
        </el-alert>
        <el-form label-width="100px" style="max-width:500px">
          <el-form-item label="API 地址">
            <el-input v-model="openaiBaseUrl" placeholder="https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="openaiApiKey" placeholder="sk-..." show-password />
          </el-form-item>
        </el-form>
        <div style="margin-top:4px;margin-bottom:16px;margin-left:100px;display:flex;gap:8px;align-items:center">
          <el-button type="primary" :loading="savingOpenai" @click="saveOpenaiSettings">保存设置</el-button>
          <el-button :loading="testingOpenai" @click="testOpenaiConn">测试连接</el-button>
        </div>
        <div v-if="openaiTestResult" style="margin-bottom:16px;margin-left:100px;max-width:400px">
          <el-alert :type="openaiTestResult.ok ? 'success' : 'error'" :closable="false" :title="openaiTestResult.msg" />
        </div>
      </template>

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

      <el-divider />
      <h3 style="margin-bottom:16px">1688 采集书签工具</h3>
      <el-alert type="success" :closable="false" style="margin-bottom:16px">
        <p>将下方按钮拖到浏览器书签栏，即可在 1688 商品页面一键采集产品信息到系统中，无需配置 Cookie。导入结果会在页面右上角弹窗提示，不会打开新窗口。</p>
        <ol style="margin:8px 0 0 16px;line-height:2">
          <li>将下方的 <b>"采集到系统"</b> 按钮<b>拖拽</b>到浏览器书签栏</li>
          <li>打开任意 1688 商品详情页</li>
          <li>点击书签栏中的 "采集到系统" 按钮</li>
          <li>系统会自动提取产品标题、主图、厂家并导入，结果显示在页面右上角</li>
        </ol>
      </el-alert>
      <div style="margin-bottom:12px">
        <span style="margin-right:8px">书签按钮（拖到书签栏）：</span>
        <a :href="bookmarkletCode" class="bookmarklet-btn" @click.prevent="ElMessage.info('请将此按钮拖拽到浏览器书签栏')">采集到系统</a>
      </div>
      <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <span>导入目标：</span>
        <el-radio-group v-model="bookmarkletTag" @change="updateBookmarklet">
          <el-radio-button label="">产品列表</el-radio-button>
          <el-radio-button label="done">已做产品</el-radio-button>
          <el-radio-button label="infringe">侵权产品</el-radio-button>
        </el-radio-group>
      </div>
      <el-alert type="info" :closable="false">
        <p>切换"导入目标"后需要重新拖拽书签按钮到书签栏。书签会自动使用当前登录账号，无需因切换账号而重新拖拽。</p>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { productApi, todoApi } from '@/api'
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

const proxyValue = ref('')
const proxyConfigured = ref(false)
const savingProxy = ref(false)
const deletingProxy = ref(false)
const testingProxy = ref(false)
const proxyTestResult = ref<{ ok: boolean; msg: string } | null>(null)

const openaiBaseUrl = ref('')
const openaiApiKey = ref('')
const savingOpenai = ref(false)
const testingOpenai = ref(false)
const openaiTestResult = ref<{ ok: boolean; msg: string } | null>(null)

const bookmarkletTag = ref('')

function updateBookmarklet() {}

const bookmarkletCode = computed(() => {
  const baseUrl = window.location.origin
  const tag = bookmarkletTag.value
  const code = `javascript:void(function(){
if(!location.hostname.includes('1688.com')){alert('请在1688商品页面使用');return;}
var h=document.documentElement.innerHTML;
var t=document.title||'';
var suffixes=['-1688.com','-阿里巴巴','- 阿里巴巴'];
for(var i=0;i<suffixes.length;i++){if(t.endsWith(suffixes[i]))t=t.slice(0,-suffixes[i].length).trim();}
var parts=t.split('-');
var title=parts.slice(0,-1).join('-').trim()||t;
var mfr=parts.length>1?parts[parts.length-1].trim():'';
var img='';
var imgPats=[/"imageUrl"\\s*:\\s*"((?:https?:)?\\/\\/[^"]+)"/,/"imgUrl"\\s*:\\s*"((?:https?:)?\\/\\/[^"]+)"/,/"originalImageURI"\\s*:\\s*"((?:https?:)?\\/\\/[^"]+)"/,/"searchImageUrl"\\s*:\\s*"((?:https?:)?\\/\\/[^"]+)"/,/"picUrl"\\s*:\\s*"((?:https?:)?\\/\\/[^"]+)"/,/"coverImage"\\s*:\\s*"((?:https?:)?\\/\\/[^"]+)"/,/"image"\\s*:\\s*"((?:https?:)?\\/\\/[^"]*alicdn\\.com[^"]*)"/];
for(var p=0;p<imgPats.length;p++){var mm=h.match(imgPats[p]);if(mm){img=mm[1];break;}}
if(!img){var om=document.querySelector('meta[property="og:image"]')||document.querySelector('meta[name="og:image"]');if(om&&om.content&&om.content.indexOf('alicdn')>-1)img=om.content;}
if(!img){var imgs=document.querySelectorAll('img');for(var j=0;j<imgs.length;j++){var s=imgs[j].src||imgs[j].dataset.src||imgs[j].dataset.lazySrc||imgs[j].dataset.imgSrc||'';if(s.indexOf('alicdn.com')>-1&&s.indexOf('.gif')<0&&s.indexOf('.svg')<0&&s.indexOf('.ico')<0){var w=parseInt(imgs[j].naturalWidth||imgs[j].width||0);var ht=parseInt(imgs[j].naturalHeight||imgs[j].height||0);if((w&&w<50)||(ht&&ht<50))continue;img=s;break;}}}
if(!img){var bgEls=document.querySelectorAll('[style*="background"]');for(var b=0;b<bgEls.length;b++){var bgm=(bgEls[b].style.backgroundImage||'').match(/url\\(["']?((?:https?:)?\\/\\/[^"')]*alicdn\\.com[^"')]*\\.(?:jpg|jpeg|png|webp)[^"')]*)["']?\\)/i);if(bgm){img=bgm[1];break;}}}
if(img&&img.startsWith('//'))img='https:'+img;
if(!mfr){var mfrPats=[/"companyName"\\s*:\\s*"([^"]+)"/,/"supplierName"\\s*:\\s*"([^"]+)"/,/"sellerName"\\s*:\\s*"([^"]+)"/];for(var k=0;k<mfrPats.length;k++){var mf=h.match(mfrPats[k]);if(mf){mfr=mf[1];break;}}}
var el=document.getElementById('_prs_toast');if(!el){el=document.createElement('div');el.id='_prs_toast';el.style.cssText='position:fixed;top:20px;right:20px;z-index:2147483647;padding:16px 24px;border-radius:8px;font-size:14px;color:#fff;box-shadow:0 4px 12px rgba(0,0,0,.3);transition:opacity .5s;font-family:sans-serif;max-width:360px;line-height:1.5;';document.body.appendChild(el);}
el.style.background='#409EFF';el.style.opacity='1';el.textContent='\\u23f3 正在导入...';
var params=new URLSearchParams({title:title,url:location.href,image:img,manufacturer:mfr,tag:'${tag}'});
window.open('${baseUrl}/bookmarklet-import?'+params.toString(),'pas_import','width=500,height=280,top=100,left=100');
window.addEventListener('message',function handler(e){if(!e.data||e.data.type!=='prs_result')return;window.removeEventListener('message',handler);if(e.data.ok){el.style.background='#67C23A';el.textContent='\\u2714 导入成功: '+String(e.data.name||'').substring(0,30);}else{el.style.background='#F56C6C';el.textContent='\\u2718 导入失败: '+String(e.data.err||'未知错误');}setTimeout(function(){el.style.opacity='0';},3000);});
})()`
  return code.replace(/\n/g, '')
})

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
    try {
      const res: any = await productApi.getProxy()
      proxyConfigured.value = res.data.configured
      if (res.data.proxy_url) proxyValue.value = res.data.proxy_url
    } catch {}
    try {
      const res: any = await todoApi.getOpenaiSettings()
      if (res.data.base_url) openaiBaseUrl.value = res.data.base_url
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

async function saveProxy() {
  if (!proxyValue.value.trim()) return ElMessage.warning('请输入代理地址')
  savingProxy.value = true
  try {
    await productApi.setProxy(proxyValue.value.trim())
    ElMessage.success('代理已保存')
    proxyConfigured.value = true
  } catch (e: any) {
    ElMessage.error(e || '保存失败')
  } finally {
    savingProxy.value = false
  }
}

async function deleteProxy() {
  deletingProxy.value = true
  try {
    await productApi.deleteProxy()
    ElMessage.success('代理已删除')
    proxyConfigured.value = false
    proxyValue.value = ''
  } catch (e: any) {
    ElMessage.error(e || '删除失败')
  } finally {
    deletingProxy.value = false
  }
}

async function testProxy() {
  testingProxy.value = true
  proxyTestResult.value = null
  try {
    const res: any = await productApi.scrape('https://detail.1688.com/offer/622463490498.html')
    if (res.data?.error) {
      proxyTestResult.value = { ok: false, msg: `爬取失败: ${res.data.error}` }
    } else if (res.data?.title) {
      proxyTestResult.value = { ok: true, msg: `代理正常，获取到: ${res.data.title}` }
    } else {
      proxyTestResult.value = { ok: false, msg: '未获取到数据，代理可能不可用' }
    }
  } catch (e: any) {
    proxyTestResult.value = { ok: false, msg: e || '测试失败' }
  } finally {
    testingProxy.value = false
  }
}

async function saveOpenaiSettings() {
  savingOpenai.value = true
  openaiTestResult.value = null
  try {
    await todoApi.setOpenaiSettings({ api_key: openaiApiKey.value.trim(), base_url: openaiBaseUrl.value.trim() })
    ElMessage.success('AI 设置已保存')
    if (openaiApiKey.value.trim()) openaiApiKey.value = ''
  } catch (e: any) {
    ElMessage.error(e || '保存失败')
  } finally {
    savingOpenai.value = false
  }
}

async function testOpenaiConn() {
  testingOpenai.value = true
  openaiTestResult.value = null
  try {
    const res: any = await todoApi.testOpenaiConnection()
    openaiTestResult.value = res.data
  } catch (e: any) {
    openaiTestResult.value = { ok: false, msg: e || '请求失败' }
  } finally {
    testingOpenai.value = false
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

<style scoped>
.bookmarklet-btn {
  display: inline-block;
  padding: 8px 20px;
  background: linear-gradient(135deg, #409EFF, #337ecc);
  color: #fff;
  border-radius: 6px;
  text-decoration: none;
  font-weight: bold;
  font-size: 14px;
  cursor: grab;
  user-select: none;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.4);
}
.bookmarklet-btn:hover {
  background: linear-gradient(135deg, #66b1ff, #409EFF);
}
</style>
