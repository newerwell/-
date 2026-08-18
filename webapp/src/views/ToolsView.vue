<script setup lang="ts">
import { ref } from "vue";

const tools = ref([
  {
    name: "get_weather",
    desc: "查询指定城市的当前天气和未来三天预报。",
    example: "北京天气怎么样",
    icon: "Sunny",
  },
  {
    name: "web_search",
    desc: "在互联网上搜索信息，返回相关网页的标题、链接和摘要。",
    example: "搜索今天的新闻热点",
    icon: "Search",
  },
  {
    name: "set_reminder",
    desc: "设置提醒，支持倒计时（X分钟后）或定时（几点几分）。",
    example: "5分钟后提醒我喝水",
    icon: "AlarmClock",
  },
]);

const tip = ref("在「对话」页直接输入上面的示例语句即可触发对应工具。");
</script>

<template>
  <div class="tools-view">
    <el-alert
      :title="tip"
      type="info"
      :closable="false"
      class="tools-tip"
    />
    <el-row :gutter="16" class="tools-grid">
      <el-col v-for="t in tools" :key="t.name" :xs="24" :sm="8">
        <el-card class="tool-card" shadow="hover">
          <template #header>
            <div class="tool-card-header">
              <el-icon :size="20"><component :is="t.icon" /></el-icon>
              <span>{{ t.name }}</span>
            </div>
          </template>
          <p class="tool-desc">{{ t.desc }}</p>
          <el-tag size="small" type="info" effect="plain" class="tool-example">
            示例: {{ t.example }}
          </el-tag>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.tools-view {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}
.tools-tip {
  margin-bottom: 16px;
}
.tools-grid {
  margin-top: 4px;
}
.tool-card {
  margin-bottom: 16px;
}
.tool-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.tool-desc {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.6;
  min-height: 44px;
}
.tool-example {
  margin-top: 8px;
}
</style>
