<template>
  <el-card>
    <h2>欢迎，{{ auth.user?.real_name }}</h2>
    <p>当前角色：{{ roleLabel }}</p>
    <el-row :gutter="20" style="margin-top:24px">
      <el-col :span="8">
        <el-card shadow="hover" class="shortcut" @click="router.push('/products')">
          <el-icon size="32"><Goods /></el-icon>
          <div>产品列表</div>
        </el-card>
      </el-col>
      <el-col v-if="auth.user?.role !== 'selector'" :span="8">
        <el-card shadow="hover" class="shortcut" @click="router.push('/reviews')">
          <el-icon size="32"><Check /></el-icon>
          <div>待审核列表</div>
        </el-card>
      </el-col>
      <el-col v-if="auth.user?.role === 'admin'" :span="8">
        <el-card shadow="hover" class="shortcut" @click="router.push('/users')">
          <el-icon size="32"><User /></el-icon>
          <div>用户管理</div>
        </el-card>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Goods, Check, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const roleLabel = computed(() => ({ admin: '管理员', selector: '选品员', reviewer: '审核员' }[auth.user?.role ?? ''] ?? ''))
</script>

<style scoped>
.shortcut { text-align:center; cursor:pointer; padding:20px; }
.shortcut div { margin-top:8px; font-size:14px; }
</style>
