import { createRouter, createWebHistory } from "vue-router";
import ChatView from "@/views/ChatView.vue";
import ToolsView from "@/views/ToolsView.vue";
import AboutView from "@/views/AboutView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "chat",
      component: ChatView,
      meta: { title: "对话" },
    },
    {
      path: "/tools",
      name: "tools",
      component: ToolsView,
      meta: { title: "工具" },
    },
    {
      path: "/about",
      name: "about",
      component: AboutView,
      meta: { title: "关于" },
    },
  ],
});

router.afterEach((to) => {
  const title = to.meta.title as string | undefined;
  document.title = title ? `${title} - 本地语音助手` : "本地语音助手";
});

export default router;
