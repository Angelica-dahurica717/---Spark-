<!-- 谣言库检索页。支持关键词、主题下拉、日期选择器多维筛选，带分页，点击行可查看原文链接，调用 /api/rumors/list 接口 -->

<template>
  <div class="rumor-search-container">
    <el-card shadow="never">
      <!-- 搜索表单 -->
      <el-form :inline="true" :model="searchForm" class="search-form" size="default">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="搜索标题或内容" clearable @keyup.enter="handleSearch" style="width: 200px" />
        </el-form-item>
        
        <el-form-item label="所属主题">
          <el-select v-model="searchForm.topic" placeholder="全部主题" clearable style="width: 160px">
            <el-option
              v-for="(item, index) in topics"
              :key="index"
              :label="item.label"
              :value="index"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="发布日期">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">检索</el-button>
          <el-button :icon="Refresh" @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 数据表格 -->
      <el-table 
        v-loading="loading" 
        :data="tableData" 
        stripe 
        border 
        style="width: 100%"
        :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="title" label="文章标题" min-width="250" show-overflow-tooltip>
          <template #default="scope">
            <el-link type="primary" :href="scope.row.url" target="_blank">{{ scope.row.title }}</el-link>
          </template>
        </el-table-column>
        <el-table-column label="归属主题" width="120" align="center">
          <template #default="scope">
            <el-tag :type="getTopicTagType(scope.row.dominant_topic)">
              {{ getTopicLabel(scope.row.dominant_topic) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="160" show-overflow-tooltip />
        <el-table-column prop="publish_date" label="发布时间" width="120" align="center" />
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="scope">
            <el-button type="primary" link size="small" @click="viewDetail(scope.row.id)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="dialogVisible" title="谣言文章详情" width="60%" destroy-on-close>
      <div v-loading="detailLoading" class="detail-content" v-if="detailData">
        <h2 class="detail-title">{{ detailData.title }}</h2>
        <div class="detail-meta">
          <span>来源: {{ detailData.source || '未知' }}</span>
          <span>发布时间: {{ detailData.publish_date }}</span>
          <span>分类: {{ detailData.category || '全部' }}</span>
          <span>原始链接: <a :href="detailData.url" target="_blank">点击访问</a></span>
        </div>
        <el-divider />
        <div class="detail-text">{{ detailData.content }}</div>

      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

// 搜索参数
const searchForm = reactive({
  keyword: '',
  topic: ''
})
const dateRange = ref([])

// 表格数据
const loading = ref(false)
const tableData = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const topics = ref([])

// 详情弹窗
const dialogVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref(null)

const getTopicTagType = (tid) => {
  if (tid < 0) return 'info'
  const types = ['', 'success', 'warning', 'danger']
  return types[tid % types.length]
}

const getTopicLabel = (tid) => {
  if (tid < 0 || tid >= topics.value.length) return '未知主题'
  return topics.value[tid].label
}

const fetchTopics = async () => {
  try {
    const res = await request.get('/api/analysis/topics')
    if (res.code === 200) {
      topics.value = res.data
    }
  } catch (e) {}
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: page.value,
      size: size.value,
      keyword: searchForm.keyword,
      topic: searchForm.topic !== '' ? searchForm.topic : ''
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    
    const res = await request.get('/api/rumors/list', { params })
    if (res.code === 200) {
      tableData.value = res.data.list
      total.value = res.data.total
    }
  } catch (e) {
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  fetchData()
}

const resetSearch = () => {
  searchForm.keyword = ''
  searchForm.topic = ''
  dateRange.value = []
  handleSearch()
}

const handleSizeChange = (val) => {
  size.value = val
  fetchData()
}

const handleCurrentChange = (val) => {
  page.value = val
  fetchData()
}

const viewDetail = async (id) => {
  dialogVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    const res = await request.get(`/api/rumors/${id}`)
    if (res.code === 200) {
      detailData.value = res.data
    }
  } catch (e) {
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => {
  fetchTopics().then(() => {
    fetchData()
  })
})
</script>

<style scoped>
.rumor-search-container {
  padding: 10px;
}
.search-form {
  margin-bottom: 10px;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.detail-title {
  text-align: center;
  color: #303133;
  margin-top: 0;
}
.detail-meta {
  display: flex;
  justify-content: space-between;
  color: #909399;
  font-size: 13px;
  flex-wrap: wrap;
}
.detail-text {
  color: #606266;
  line-height: 1.8;
  white-space: pre-wrap;
  font-size: 15px;
  max-height: 400px;
  overflow-y: auto;
  padding-right: 10px;
}
</style>
