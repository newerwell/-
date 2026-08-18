<script setup lang="ts">
import { useChatStore } from "@/stores/chat";

const chat = useChatStore();
</script>

<template>
  <div class="about-view">
    <el-card class="about-card">
      <template #header>
        <div class="about-header">
          <el-icon :size="20"><Microphone /></el-icon>
          <span>本地语音助手</span>
        </div>
      </template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="架构">
          Vue 3 + TypeScript + Vite + Element Plus 前端
          <br />
          FastAPI 后端（STT / LLM / TTS / 工具调用）
        </el-descriptions-item>
        <el-descriptions-item label="后端状态">
          <el-tag v-if="chat.health?.cuda" type="success" size="small">GPU 可用</el-tag>
          <el-tag v-else-if="chat.health" type="warning" size="small">CPU 模式</el-tag>
          <el-tag v-else type="danger" size="small">未连接</el-tag>
          <span v-if="chat.health" class="gpu-info">
            显存占用 {{ chat.health.gpu_mem_gb }} GB
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="能力">
          <ul class="cap-list">
            <li>🎙️ 语音对话（录音 → 识别 → 回复 → 朗读）</li>
            <li>💬 文字对话（Qwen3-8B 4bit 本地推理）</li>
            <li>🌤️ 天气查询（Open-Meteo）</li>
            <li>🔍 网络搜索（cn.bing.com）</li>
            <li>⏰ 定时提醒（本地）</li>
            <li>🔊 回复朗读（edge-tts）</li>
          </ul>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.about-view {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}
.about-card {
  max-width: 640px;
}
.about-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.gpu-info {
  margin-left: 8px;
  color: #6b7280;
  font-size: 13px;
}
.cap-list {
  margin: 0;
  padding-left: 16px;
  line-height: 1.9;
}
</style>
