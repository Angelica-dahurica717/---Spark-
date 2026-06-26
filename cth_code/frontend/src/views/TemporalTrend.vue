<!-- 传播趋势分析页。多系列折线/柱状图，展示各主题按月的文章数量变化，调用 /api/analysis/monthly-trend 接口，支持折线图/柱状图切换 -->

<template>
  <div class="temporal-trend-container">
    <el-card shadow="never" class="trend-card">
      <template #header>
        <div class="card-header">
          <span>谣言长效传播时序走势分析</span>
          <el-radio-group v-model="chartType" size="small" @change="renderChart">
            <el-radio-button label="line">多维折线 (趋势)</el-radio-button>
            <el-radio-button label="bar">堆叠柱图 (体量)</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <div ref="lineRef" class="chart-box"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '@/utils/request'

const lineRef = ref(null)
let myChart = null
const chartType = ref('line')
let rawData = null

const renderChart = () => {
  if (!myChart || !rawData) return
  
  const options = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: {
      data: rawData.series.map(s => s.name),
      top: 10,
      type: 'scroll'
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: chartType.value === 'bar',
      data: rawData.months
    },
    yAxis: { type: 'value', name: '文章发布量 (篇)' },
    series: rawData.series.map(s => ({
      name: s.name,
      type: chartType.value,
      stack: chartType.value === 'bar' ? 'Total' : null,
      smooth: true,
      data: s.data
    }))
  }
  
  myChart.setOption(options, true) // 第二个参数true表示合并取代旧配置
}

const fetchData = async () => {
  try {
    const res = await request.get('/api/analysis/monthly-trend')
    if (res.code === 200) {
      rawData = res.data
      myChart = echarts.init(lineRef.value)
      renderChart()
    }
  } catch (err) { console.error(err) }
}

const handleResize = () => {
  myChart?.resize()
}

onMounted(async () => {
  await nextTick()
  fetchData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if(myChart) myChart.dispose()
})
</script>

<style scoped>
.temporal-trend-container {
  padding: 10px;
}
.trend-card {
  margin-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}
.chart-box {
  height: 500px;
  width: 100%;
}
</style>
