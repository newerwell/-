<script setup lang="ts">
import { onMounted } from "vue";
import { useRoute } from "vue-router";
import { useChatStore } from "@/stores/chat";

const route = useRoute();
const chat = useChatStore();

function openWelcome() {
  window.open("/welcome", "_blank");
}

onMounted(() => {
  chat.checkHealth();
  setInterval(() => chat.checkHealth(), 15000);
});
</script>

<template>
  <el-container class="app-layout">
    <!-- 侧边栏 -->
    <el-aside width="200px" class="app-aside">
      <div class="logo">
        <el-icon :size="24"><Microphone /></el-icon>
        <span>语音助手</span>
      </div>
      <el-menu :default-active="route.path" router class="side-menu">
        <el-menu-item @click="openWelcome">
          <el-icon><House /></el-icon>
          <span>欢迎页</span>
        </el-menu-item>
        <el-menu-item index="/">
          <el-icon><ChatDotRound /></el-icon>
          <span>对话</span>
        </el-menu-item>
        <el-menu-item index="/tools">
          <el-icon><Tools /></el-icon>
          <span>工具</span>
        </el-menu-item>
        <el-menu-item index="/about">
          <el-icon><InfoFilled /></el-icon>
          <span>关于</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主区 -->
    <el-container>
      <el-header class="app-header" height="48px">
        <div class="header-left">
          <span class="page-title">{{ (route.meta.title as string) || "对话" }}</span>
        </div>
        <div class="header-right">
          <el-tag v-if="chat.health?.cuda" type="success" size="small" effect="light">
            GPU 就绪
          </el-tag>
          <el-tag v-else-if="chat.health" type="warning" size="small">CPU 模式</el-tag>
          <el-tag v-else type="danger" size="small">后端未连接</el-tag>
          <el-tag v-if="chat.health" size="small" effect="plain">
            显存 {{ chat.health.gpu_mem_gb }} GB
          </el-tag>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-layout {
  height: 100vh;
}
.app-aside {
  background: #1f2937;
  display: flex;
  flex-direction: column;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  padding: 16px;
}
.side-menu {
  border-right: none;
  background: transparent;
  flex: 1;
}
.side-menu :deep(.el-menu-item) {
  color: #9ca3af;
}
.side-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: rgba(99, 102, 241, 0.3);
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}
.header-left {
  display: flex;
  align-items: center;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.app-main {
  padding: 0;
  overflow: hidden;
  background: #f9fafb;
}
</style>
