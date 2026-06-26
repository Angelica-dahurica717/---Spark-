<!-- 用户管理页（仅管理员可见）。展示用户列表，支持新增/编辑/删除用户，调用 /api/users 系列接口 -->

<template>
  <div class="user-manage-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>系统用户管理</span>
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增用户</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="tableData" stripe border style="width: 100%">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="username" label="登录账号" width="150" />
        <el-table-column prop="name" label="用户姓名" width="150" />
        <el-table-column label="包含权限角色" width="150" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'success'">
              {{ scope.row.role === 'admin' ? '系统管理员' : '数据分析员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180">
          <template #default="scope">
            <el-button size="small" type="primary" link @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(scope.row)" :disabled="scope.row.username === currentUsername">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 表单弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="500px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="请输入英文数字账号" />
        </el-form-item>
        <el-form-item label="用户姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入显示姓名" />
        </el-form-item>
        <el-form-item label="登录密码" :prop="isEdit ? '' : 'password'">
          <el-input v-model="form.password" type="password" :placeholder="isEdit ? '留空表示不修改' : '请输入密码'" show-password />
        </el-form-item>
        <el-form-item label="权限角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio label="analyst">数据分析员</el-radio>
            <el-radio label="admin">系统管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="submitLoading">保存配置</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'

const loading = ref(false)
const tableData = ref([])
const currentUsername = localStorage.getItem('username')

// 弹窗表单状态
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
const form = reactive({
  username: '',
  name: '',
  password: '',
  role: 'analyst'
})

const rules = reactive({
  username: [{ required: true, message: '账号不能为空', trigger: 'blur' }],
  name: [{ required: true, message: '姓名不能为空', trigger: 'blur' }],
  password: [{ required: true, message: '密码不能为空', trigger: 'blur' }],
  role: [{ required: true, message: '角色不能为空', trigger: 'change' }]
})

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/users')
    if (res.code === 200) tableData.value = res.data
  } catch (e) {
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, { username: '', name: '', password: '', role: 'analyst' })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, { username: row.username, name: row.name, password: '', role: row.role })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要彻底删除用户 "${row.name}" 吗？此操作不可逆。`, '危险警告', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'error',
  }).then(async () => {
    try {
      const res = await request.delete(`/api/users/${row.username}`)
      if (res.code === 200) {
        ElMessage.success('操作成功')
        fetchData()
      } else {
        ElMessage.error(res.msg || '操作失败')
      }
    } catch (e) {}
  }).catch(() => {})
}

const submitForm = () => {
  formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        let res
        if (isEdit.value) {
          const payload = { name: form.name, role: form.role }
          if (form.password) payload.password = form.password
          res = await request.put(`/api/users/${form.username}`, payload)
        } else {
          res = await request.post('/api/users', form)
        }
        if (res.code === 200) {
          ElMessage.success('保存成功')
          dialogVisible.value = false
          fetchData()
        } else {
          ElMessage.error(res.msg || '操作失败')
        }
      } catch (e) {
      } finally {
        submitLoading.value = false
      }
    }
  })
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.user-manage-container {
  padding: 10px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
</style>
