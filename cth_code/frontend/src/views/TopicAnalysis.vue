<!-- 热点主题分析页。词云图 + 饼图，调用 api/analysis/topic-distribution 接口 -->

<template>
  <div class="topic-analysis-container">
    <el-row :gutter="20">
      <!-- 词云图 -->
      <el-col :span="14">
        <el-card shadow="hover" header="全局高频词云分析">
          <div ref="wordcloudRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <!-- 饼图 -->
      <el-col :span="10">
        <el-card shadow="hover" header="八大核心主题分布占比">
          <div ref="pieRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top:20px;">
      <el-col :span="24">
        <el-card shadow="never" header="LDA主题关键词解析">
          <el-table :data="topicsTable" stripe style="width: 100%">
            <el-table-column prop="label" label="主题名称" width="150" />
            <el-table-column label="核心关键词">
              <template #default="scope">
                <el-tag 
                  v-for="(word, index) in scope.row.top_words.slice(0, 10)" 
                  :key="index" 
                  class="word-tag" 
                  :type="getTagType(index)"
                >
                  {{ word.word }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'
import request from '@/utils/request'

const wordcloudRef = ref(null)
const pieRef = ref(null)

let wordcloudChart = null
let pieChart = null

const topicsTable = ref([])

const getTagType = (idx) => {
  const types = ['', 'success', 'warning', 'danger', 'info']
  return types[idx % types.length]
}

const renderWordCloud = async () => {
  try {
    const res = await request.get('/api/analysis/wordcloud')
    if (res.code === 200) {
      // 词云图前端VUE组件
      const data = res.data.map(item => ({ name: item.word, value: item.count }))
      
      wordcloudChart = echarts.init(wordcloudRef.value)
      wordcloudChart.setOption({
        tooltip: { show: true },
        series: [{
          type: 'wordCloud',  // echarts词云图类型
          shape: 'circle',
          keepAspect: false,
          left: 'center', top: 'center', width: '90%', height: '90%',
          sizeRange: [14, 60],
          rotationRange: [-45, 90],
          rotationStep: 45,
          gridSize: 8,
          drawOutOfBound: false,
          layoutAnimation: true,
          textStyle: {
            fontFamily: 'sans-serif',
            fontWeight: 'bold',
            color: function () {
              return 'rgb(' + [
                Math.round(Math.random() * 160),
                Math.round(Math.random() * 160),
                Math.round(Math.random() * 160)
              ].join(',') + ')';
            }
          },
          emphasis: { focus: 'self', textStyle: { textShadowBlur: 10, textShadowColor: '#333' } },
          data: data
        }]
      })
    }
  } catch (err) { console.error(err) }
}

const renderPie = async () => {
  try {
    const res = await request.get('/api/analysis/topic-distribution')
    if (res.code === 200) {
      pieChart = echarts.init(pieRef.value)
      pieChart.setOption({
        tooltip: {
          trigger: 'item',
          formatter: function(params) {
            let res = `${params.name}: ${params.value}篇 (${params.percent}%)<br/>`
            if (params.data.top_words) {
              res += `典型特征: ${params.data.top_words.join(', ')}`
            }
            return res
          }
        },
        legend: { orient: 'vertical', left: 'left' },
        series: [
          {
            name: '主题发文量',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: { show: false, position: 'center' },
            emphasis: {
              label: { show: true, fontSize: 16, fontWeight: 'bold' }
            },
            labelLine: { show: false },
            data: res.data
          }
        ]
      })
    }
  } catch (err) { console.error(err) }
}

const fetchTopics = async () => {
  try {
    const res = await request.get('/api/analysis/topics')
    if (res.code === 200) topicsTable.value = res.data
  } catch(err) {}
}

const handleResize = () => {
  wordcloudChart?.resize()
  pieChart?.resize()
}

onMounted(async () => {
  await nextTick()
  renderWordCloud()
  renderPie()
  fetchTopics()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if(wordcloudChart) wordcloudChart.dispose()
  if(pieChart) pieChart.dispose()
})
</script>

<style scoped>
.topic-analysis-container {
  padding: 10px;
}
.chart-box {
  height: 380px;
  width: 100%;
}
.word-tag {
  margin-right: 8px;
  margin-bottom: 5px;
}
</style>
