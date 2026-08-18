import axios from "axios";
import type { ToolCall } from "@/stores/chat";

/** Axios 实例：走 vite 代理（dev）或同源（prod） */
const http = axios.create({
  baseURL: "",
  timeout: 300_000, // LLM 生成慢，5 分钟
});

export interface ChatResponse {
  reply: string;
  tool_calls: ToolCall[];
  history_len: number;
  tts_url?: string;
}

export interface AudioResponse {
  user_text: string;
  reply: string;
  tool_calls: ToolCall[];
  tts_url?: string;
}

export interface HealthResponse {
  status: string;
  cuda: boolean;
  gpu_mem_gb: number;
}

/** 健康检查 */
export async function healthApi(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>("/api/health");
  return data;
}

/** 文字对话 */
export async function chatApi(text: string): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>("/api/chat", { text });
  if ((data as unknown as { error?: string }).error) {
    throw new Error((data as unknown as { error: string }).error);
  }
  return data;
}

/** 语音对话（上传 wav） */
export async function audioApi(wavBlob: Blob): Promise<AudioResponse> {
  const form = new FormData();
  form.append("file", wavBlob, "voice.wav");
  const { data } = await http.post<AudioResponse>("/api/audio", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  if ((data as unknown as { error?: string }).error) {
    throw new Error((data as unknown as { error: string }).error);
  }
  return data;
}

/** 重置对话 */
export async function resetApi(): Promise<void> {
  await http.post("/api/chat", { text: "", reset: true });
}
