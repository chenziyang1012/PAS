<template>
  <el-container style="height:100vh">
    <el-aside width="200px" style="background:#304156">
      <div style="color:#fff;padding:20px;font-size:18px;font-weight:bold">产品审核系统</div>
      <el-menu router background-color="#304156" text-color="#bfcbd9" active-text-color="#409EFF" :default-active="route.path">
        <el-menu-item index="/dashboard"><el-icon><House /></el-icon>工作台</el-menu-item>
        <el-menu-item index="/products"><el-icon><Goods /></el-icon>产品列表</el-menu-item>
        <el-menu-item v-if="auth.user?.role !== 'selector'" index="/reviews"><el-icon><Check /></el-icon>待审核</el-menu-item>
        <el-menu-item v-if="auth.user?.role !== 'reviewer'" index="/todo"><el-icon><List /></el-icon>待做列表</el-menu-item>
        <el-menu-item index="/done"><el-icon><Finished /></el-icon>已做产品</el-menu-item>
        <el-menu-item index="/infringe"><el-icon><Warning /></el-icon>侵权产品</el-menu-item>
        <el-menu-item v-if="auth.user?.role === 'admin'" index="/users"><el-icon><User /></el-icon>用户管理</el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon>系统设置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background:#fff;display:flex;align-items:center;justify-content:flex-end;border-bottom:1px solid #eee">
        <span style="margin-right:16px">{{ auth.user?.username }}（{{ roleLabel }}）</span>
        <el-button type="text" @click="handleLogout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { House, Goods, Check, User, Finished, Warning, Setting, List } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const roleLabel = computed(() => ({ admin: '管理员', selector: '选品员', reviewer: '审核员' }[auth.user?.role ?? ''] ?? ''))

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
