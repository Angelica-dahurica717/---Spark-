<!-- 系统概览仪表盘。展示总文章数、涵盖月份数、数据时间范围4张统计卡片，调用 /api/analysis/stats 接口 -->

<template>
  <div class="dashboard-container">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-blue"><el-icon><Document /></el-icon></div>
          <div class="stat-info">
            <div class="stat-title">谣言文章总数</div>
            <div class="stat-value">{{ stats.total_articles || 0 }} 篇</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-green"><el-icon><Calendar /></el-icon></div>
          <div class="stat-info">
            <div class="stat-title">数据跨越月数</div>
            <div class="stat-value">{{ stats.total_months || 0 }} 个月</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-purple"><el-icon><PieChart /></el-icon></div>
          <div class="stat-info">
            <div class="stat-title">挖掘主题数量</div>
            <div class="stat-value">{{ stats.num_topics || 0 }} 个</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon bg-orange"><el-icon><Timer /></el-icon></div>
          <div class="stat-info">
            <div class="stat-title">数据时间范围</div>
            <div class="stat-value text-range">
              {{ stats.date_range?.start || '-' }}<br/>至<br/>{{ stats.date_range?.end || '-' }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="never" header="系统介绍">
          <div class="intro-content">
            <p>欢迎使用 <strong>谣言热点发现与传播分析系统</strong>。</p>
            <p>本系统基于爬虫技术从中国互联网联合辟谣平台采集全量谣言辟谣文章，利用 <strong>Spark 分布式计算框架</strong> 进行海量文本处理与清洗。</p>
            <p>通过使用 <strong>LDA (Latent Dirichlet Allocation) 主题模型</strong>，系统从杂乱的文本中自动挖掘出的潜在主题分布，并结合前端可视化手段展现谣言事件的语义特征、各主题比重，以及随时间的网络传播演化趋势。</p>
            <el-divider />
            <div class="bottom-row">
              <p class="role-notice">您当前以 [{{ userRoleName }}] 身份登录。如有数据权限疑问，请联系管理员。</p>
              <el-button type="primary" :loading="reportLoading" @click="downloadReport">
                <el-icon style="margin-right:4px"><Download /></el-icon>
                生成分析报告
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Document, Calendar, PieChart, Timer, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/request'

const stats = ref({})
const reportLoading = ref(false)

const userRoleName = computed(() => {
  return sessionStorage.getItem('role') === 'admin' ? '系统管理员' : '数据分析员'
})

const fetchStats = async () => {
  try {
    const res = await request.get('/api/analysis/stats')
    if (res.code === 200) {
      stats.value = res.data
    }
  } catch (err) {
    console.error(err)
  }
}

const downloadReport = async () => {
  reportLoading.value = true
  try {
    const token = sessionStorage.getItem('token')
    const res = await fetch('/api/analysis/report', {
      headers: { 'Authorization': 'Bearer ' + token }
    })
    if (!res.ok) throw new Error('报告生成失败')
    const blob = await res.blob()
    const now = new Date()
    const stamp = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `谣言分析报告_${stamp}.html`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('报告已下载，用浏览器打开即可查看，Ctrl+P 可打印为 PDF')
  } catch (e) {
    ElMessage.error('报告生成失败：' + e.message)
  } finally {
    reportLoading.value = false
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.dashboard-container {
  padding: 10px;
}
.stat-card {
  display: flex;
  align-items: center;
  height: 120px;
}
:deep(.el-card__body) {
  display: flex;
  width: 100%;
  padding: 20px;
}
.stat-icon {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 36px;
  color: #fff;
  margin-right: 20px;
}
.bg-blue { background: #409EFF; }
.bg-green { background: #67C23A; }
.bg-purple { background: #909399; }
.bg-orange { background: #E6A23C; }

.stat-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.stat-title {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}
.text-range {
  font-size: 14px;
  line-height: 1.4;
  font-weight: normal;
}

.intro-content {
  color: #606266;
  line-height: 1.8;
  font-size: 15px;
}
.role-notice {
  color: #E6A23C;
  font-style: italic;
}
.bottom-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
