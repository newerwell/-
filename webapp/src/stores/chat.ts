import { defineStore } from "pinia";
import { ref } from "vue";
import { chatApi, audioApi, healthApi } from "@/api";

/** 消息类型 */
export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
}

export interface Message {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  tools?: ToolCall[];
  ttsUrl?: string;
  loading?: boolean;
}

/** 后端健康状态 */
export interface HealthInfo {
  status: string;
  cuda: boolean;
  gpu_mem_gb: number;
}

export const useChatStore = defineStore("chat", () => {
  const messages = ref<Message[]>([]);
  const busy = ref(false);
  const health = ref<HealthInfo | null>(null);
  let nextId = 1;

  function addMessage(
    role: Message["role"],
    content: string,
    extra?: Partial<Message>
  ): Message {
    const msg: Message = { id: nextId++, role, content, ...extra };
    messages.value.push(msg);
    return msg;
  }

  function updateMessage(id: number, patch: Partial<Message>) {
    const m = messages.value.find((x) => x.id === id);
    if (m) Object.assign(m, patch);
  }

  async function checkHealth(): Promise<HealthInfo | null> {
    try {
      health.value = await healthApi();
      return health.value;
    } catch {
      health.value = null;
      return null;
    }
  }

  /** 发送文字消息 */
  async function sendText(text: string) {
    if (!text.trim() || busy.value) return;
    busy.value = true;
    addMessage("user", text);
    const ai = addMessage("assistant", "", { loading: true });
    try {
      const data = await chatApi(text);
      updateMessage(ai.id, {
        content: data.reply,
        tools: data.tool_calls,
        ttsUrl: data.tts_url || undefined,
        loading: false,
      });
    } catch (e: unknown) {
      updateMessage(ai.id, {
        content: "⚠️ " + (e as Error).message,
        loading: false,
      });
    } finally {
      busy.value = false;
    }
  }

  /** 发送语音消息 */
  async function sendAudio(wavBlob: Blob) {
    if (busy.value) return;
    busy.value = true;
    const user = addMessage("user", "🎤 语音输入...", { loading: true });
    const ai = addMessage("assistant", "", { loading: true });
    try {
      const data = await audioApi(wavBlob);
      updateMessage(user.id, {
        content: "🎤 你说：" + (data.user_text || "(未识别)"),
        loading: false,
      });
      updateMessage(ai.id, {
        content: data.reply,
        tools: data.tool_calls,
        ttsUrl: data.tts_url || undefined,
        loading: false,
      });
    } catch (e: unknown) {
      updateMessage(user.id, { content: "🎤 语音输入失败", loading: false });
      updateMessage(ai.id, {
        content: "⚠️ " + (e as Error).message,
        loading: false,
      });
    } finally {
      busy.value = false;
    }
  }

  function reset() {
    messages.value = [];
  }

  return {
    messages,
    busy,
    health,
    addMessage,
    updateMessage,
    checkHealth,
    sendText,
    sendAudio,
    reset,
  };
});
