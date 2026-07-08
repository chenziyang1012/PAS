<template>
  <div>
    <el-card>
      <div style="display:flex;justify-content:space-between;margin-bottom:16px">
        <div style="display:flex;gap:8px">
          <el-input v-model="query.username" placeholder="用户名" clearable style="width:160px" @change="load" />
          <el-select v-model="query.role" placeholder="角色" clearable style="width:120px" @change="load">
            <el-option label="管理员" value="admin" /><el-option label="选品员" value="selector" /><el-option label="审核员" value="reviewer" />
          </el-select>
          <el-select v-model="query.status" placeholder="状态" clearable style="width:100px" @change="load">
            <el-option label="启用" value="enabled" /><el-option label="禁用" value="disabled" />
          </el-select>
        </div>
        <el-button type="primary" @click="openCreate">新增用户</el-button>
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="real_name" label="姓名" />
        <el-table-column prop="role" label="角色">
          <template #default="{row}">{{ roleMap[row.role] }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态">
          <template #default="{row}"><el-tag :type="row.status==='enabled'?'success':'danger'">{{ row.status==='enabled'?'启用':'禁用' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{row}">{{ row.created_at?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{row}">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" :type="row.status==='enabled'?'warning':'success'" @click="toggleStatus(row)">{{ row.status==='enabled'?'禁用':'启用' }}</el-button>
            <el-button size="small" @click="resetPwd(row)">重置密码</el-button>
            <el-button size="small" type="danger" @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination style="margin-top:16px" v-model:current-page="query.page" :page-size="20" :total="total" @current-change="load" layout="total,prev,pager,next" />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId?'编辑用户':'新增用户'" width="400px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="form.username" :disabled="!!editId" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" :placeholder="editId?'不填则不修改':'请输入密码'" /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.real_name" /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width:100%">
            <el-option label="管理员" value="admin" /><el-option label="选品员" value="selector" /><el-option label="审核员" value="reviewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="启用" value="enabled" /><el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { userApi } from '@/api'

const roleMap: Record<string,string> = { admin:'管理员', selector:'选品员', reviewer:'审核员' }
const list = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editId = ref<number|null>(null)
const query = reactive({ page: 1, username: '', role: '', status: '' })
const form = reactive({ username:'', password:'', real_name:'', role:'selector', status:'enabled' })

async function load() {
  loading.value = true
  try {
    const res: any = await userApi.list({ ...query, page_size: 20 })
    list.value = res.data.items; total.value = res.data.total
  } finally { loading.value = false }
}

function openCreate() {
  editId.value = null
  Object.assign(form, { username:'', password:'', real_name:'', role:'selector', status:'enabled' })
  dialogVisible.value = true
}

function openEdit(row: any) {
  editId.value = row.id
  Object.assign(form, { username:row.username, password:'', real_name:row.real_name, role:row.role, status:row.status })
  dialogVisible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editId.value) await userApi.update(editId.value, form)
    else await userApi.create(form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch(e:any) { ElMessage.error(e) } finally { saving.value = false }
}

async function toggleStatus(row: any) {
  const s = row.status === 'enabled' ? 'disabled' : 'enabled'
  await userApi.updateStatus(row.id, s)
  row.status = s
}

async function resetPwd(row: any) {
  const { value } = await ElMessageBox.prompt('请输入新密码', '重置密码', { inputType:'password' })
  await userApi.resetPassword(row.id, value)
  ElMessage.success('密码已重置')
}

async function deleteUser(row: any) {
  try {
    await ElMessageBox.confirm(`确定要删除用户「${row.real_name || row.username}」吗？此操作不可撤销。`, '删除用户', { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' })
    await userApi.delete(row.id)
    ElMessage.success('用户已删除')
    load()
  } catch(e: any) {
    if (e !== 'cancel') ElMessage.error(e || '删除失败')
  }
}

onMounted(load)
</script>
