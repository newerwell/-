<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import { useChatStore } from "@/stores/chat";
import { blobToWav16k } from "@/utils/audio";

const chat = useChatStore();
const input = ref("");
const recording = ref(false);
const micTip = ref("");
const msgListRef = ref<HTMLElement | null>(null);

// ---- 音频输入设备 ----
interface MicDevice {
  deviceId: string;
  label: string;
}

const micDevices = ref<MicDevice[]>([]);
const selectedDevice = ref("");
const devicesLoading = ref(false);

async function refreshDevices() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  devicesLoading.value = true;
  try {
    // 先请求权限，否则 label 为空
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
    } catch {
      // 权限被拒时仍尝试枚举（label 可能为空）
    }
    const devices = await navigator.mediaDevices.enumerateDevices();
    const inputs = devices
      .filter((d) => d.kind === "audioinput")
      .map((d) => ({
        deviceId: d.deviceId,
        label: d.label || `麦克风 ${d.deviceId.slice(0, 8)}...`,
      }));
    // 去重（同一设备可能多次出现）
    const seen = new Set<string>();
    const unique = inputs.filter((d) => {
      if (seen.has(d.deviceId)) return false;
      seen.add(d.deviceId);
      return true;
    });
    micDevices.value = unique;
    // 默认选第一个（或保留当前选择）
    if (unique.length > 0) {
      const stillExists = unique.some((d) => d.deviceId === selectedDevice.value);
      if (!stillExists) selectedDevice.value = unique[0].deviceId;
    }
  } catch (e) {
    micTip.value = "设备枚举失败: " + (e as Error).message;
  } finally {
    devicesLoading.value = false;
  }
}

function getMicConstraints() {
  if (selectedDevice.value) {
    return { audio: { deviceId: { exact: selectedDevice.value } } };
  }
  return { audio: true };
}

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

async function scrollToBottom() {
  await nextTick();
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight;
  }
}

async function sendText() {
  const text = input.value.trim();
  if (!text || chat.busy) return;
  input.value = "";
  await chat.sendText(text);
  scrollToBottom();
}

onMounted(refreshDevices);

// ---- 录音 ----
async function toggleRecord() {
  if (recording.value) {
    stopRecord();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    micTip.value = "浏览器不支持录音";
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia(getMicConstraints());
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      micTip.value = "转换音频...";
      try {
        const wav = await blobToWav16k(new Blob(audioChunks));
        if (wav.size > 1000) {
          await chat.sendAudio(wav);
        } else {
          micTip.value = "录音太短";
        }
      } catch (e) {
        micTip.value = "音频转换失败: " + (e as Error).message;
      }
      scrollToBottom();
    };
    mediaRecorder.start();
    recording.value = true;
    micTip.value = "正在录音，点击停止";
  } catch (e) {
    micTip.value = "无法访问麦克风: " + (e as Error).message;
  }
}

function stopRecord() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  recording.value = false;
  micTip.value = "识别中...";
}

// ---- 播放 TTS（后台异步生成，重试等待就绪）----
async function playTTS(url: string) {
  const tries = 6;
  for (let i = 0; i < tries; i++) {
    try {
      const audio = new Audio(url);
      await audio.play();
      return;
    } catch (e) {
      // 文件未就绪（后台 TTS 还在合成）或播放被拒，等待后重试
      await new Promise((r) => setTimeout(r, 1500));
    }
  }
}

async function resetChat() {
  chat.reset();
}
</script>

<template>
  <div class="chat-view">
    <!-- 消息区 -->
    <div ref="msgListRef" class="msg-list">
      <template v-for="m in chat.messages" :key="m.id">
        <el-alert
          v-if="m.role === 'system'"
          :title="m.content"
          type="info"
          :closable="false"
          class="msg-system"
        />
        <div v-else class="msg-row" :class="m.role">
          <div class="msg-bubble" :class="m.role">
            <div v-if="m.loading" class="msg-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              思考中...
            </div>
            <template v-else>
              <div class="msg-content">{{ m.content }}</div>
              <!-- 工具调用 -->
              <div
                v-for="(t, i) in m.tools"
                :key="i"
                class="tool-card"
              >
                <div class="tool-name">
                  <el-icon><MagicStick /></el-icon>
                  {{ t.name }}
                </div>
                <div class="tool-args">参数: {{ JSON.stringify(t.arguments) }}</div>
                <div v-if="t.result" class="tool-result">{{ t.result }}</div>
              </div>
              <!-- TTS 播放 -->
              <div v-if="m.ttsUrl" class="msg-tts">
                <el-button
                  size="small"
                  circle
                  @click="playTTS(m.ttsUrl!)"
                >
                  <el-icon><CaretRight /></el-icon>
                </el-button>
                <span>播放语音</span>
              </div>
            </template>
          </div>
        </div>
      </template>
    </div>

    <!-- 输入区 -->
    <div class="input-area">
      <div v-if="micTip" class="mic-tip">{{ micTip }}</div>
      <!-- 麦克风设备选择 -->
      <div class="device-bar">
        <el-icon class="device-icon"><Microphone /></el-icon>
        <el-select
          v-model="selectedDevice"
          placeholder="选择语音输入设备"
          size="small"
          :loading="devicesLoading"
          class="device-select"
          @visible-change="(v: boolean) => v && refreshDevices()"
        >
          <el-option
            v-for="d in micDevices"
            :key="d.deviceId"
            :label="d.label"
            :value="d.deviceId"
          />
        </el-select>
        <el-button
          text
          size="small"
          :loading="devicesLoading"
          @click="refreshDevices"
        >
          <el-icon><Refresh /></el-icon>
        </el-button>
      </div>
      <div class="input-bar">
        <el-button
          :type="recording ? 'danger' : 'default'"
          circle
          :disabled="chat.busy"
          @click="toggleRecord"
        >
          <el-icon :size="18">
            <Microphone v-if="!recording" />
            <VideoPause v-else />
          </el-icon>
        </el-button>
        <el-input
          v-model="input"
          placeholder="输入消息，回车发送..."
          :disabled="chat.busy"
          clearable
          @keyup.enter="sendText"
        />
        <el-button type="primary" circle :disabled="chat.busy" @click="sendText">
          <el-icon :size="18"><Promotion /></el-icon>
        </el-button>
      </div>
      <div class="input-tools">
        <el-button text size="small" @click="resetChat">
          <el-icon><RefreshLeft /></el-icon> 重置对话
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.msg-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.msg-system {
  margin: 8px auto;
  max-width: 80%;
}
.msg-row {
  display: flex;
  margin-bottom: 12px;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}
.msg-bubble.user {
  background: #6366f1;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble.assistant {
  background: #fff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 4px;
}
.msg-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9ca3af;
}
.msg-content {
  white-space: pre-wrap;
}
.tool-card {
  margin-top: 8px;
  padding: 8px 10px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 12px;
  color: #1e40af;
}
.tool-name {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
}
.tool-args {
  color: #3b82f6;
  margin-top: 2px;
}
.tool-result {
  color: #6b7280;
  margin-top: 4px;
}
.msg-tts {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6366f1;
}
.input-area {
  padding: 12px 16px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.mic-tip {
  text-align: center;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
  min-height: 16px;
}
.device-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.device-icon {
  color: #6b7280;
}
.device-select {
  flex: 1;
  max-width: 320px;
}
.input-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}
.input-tools {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}
</style>
