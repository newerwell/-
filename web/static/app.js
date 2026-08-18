/**
 * 语音助手前端（Vue 3 单页应用）
 * 功能：文字对话（含工具）、语音对话（录音→后端→播放TTS）
 */
const { createApp, ref, reactive, nextTick } = Vue;

createApp({
  setup() {
    // ---- 状态 ----
    const messages = ref([]);          // [{role, content, tools}]
    const input = ref("");
    const status = ref("idle");        // idle | busy | err
    const statusText = ref("就绪");
    const isRecording = ref(false);
    const micTip = ref("");
    const isListening = ref(false);    // 是否在监听麦克风
    const ws = ref(null);
    // 音频输入设备
    const micDevices = ref([]);
    const selectedDevice = ref("");

    // ---- 设备枚举 ----
    async function refreshDevices() {
      if (!navigator.mediaDevices?.enumerateDevices) return;
      try {
        // 先请求权限让 label 可见
        try {
          const s = await navigator.mediaDevices.getUserMedia({ audio: true });
          s.getTracks().forEach((t) => t.stop());
        } catch (e) {}
        const devices = await navigator.mediaDevices.enumerateDevices();
        const seen = new Set();
        const inputs = [];
        for (const d of devices) {
          if (d.kind === "audioinput" && !seen.has(d.deviceId)) {
            seen.add(d.deviceId);
            inputs.push({ deviceId: d.deviceId, label: d.label || "麦克风 " + d.deviceId.slice(0, 8) });
          }
        }
        micDevices.value = inputs;
        if (inputs.length > 0) {
          const still = inputs.some((d) => d.deviceId === selectedDevice.value);
          if (!still) selectedDevice.value = inputs[0].deviceId;
        }
      } catch (e) {
        micTip.value = "设备枚举失败: " + e.message;
      }
    }

    function getMicConstraints() {
      return selectedDevice.value
        ? { audio: { deviceId: { exact: selectedDevice.value } } }
        : { audio: true };
    }

    // ---- 工具函数 ----
    function addMsg(role, content, tools) {
      messages.value.push({ role, content: content || "", tools: tools || [] });
      nextTick(() => {
        const box = document.querySelector(".messages");
        if (box) box.scrollTop = box.scrollHeight;
      });
    }

    function setStatus(s, text) {
      status.value = s;
      statusText.value = text;
    }

    async function healthCheck() {
      try {
        const r = await fetch("/api/health");
        const d = await r.json();
        setStatus("ok", d.cuda ? "GPU 就绪" : "CPU 模式");
      } catch (e) {
        setStatus("err", "后端未连接");
      }
    }

    // ---- 文字对话 ----
    async function sendText() {
      const text = input.value.trim();
      if (!text || status.value === "busy") return;
      input.value = "";
      addMsg("user", text);
      addMsg("assistant", "");
      setStatus("busy", "思考中...");

      // 找最后一条 assistant 消息做流式占位
      const lastIdx = messages.value.length - 1;
      try {
        const r = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        const d = await r.json();
        if (d.error) throw new Error(d.error);
        messages.value[lastIdx].content = d.reply;
        messages.value[lastIdx].tools = d.tool_calls || [];
        setStatus("ok", "就绪");
        // 播放 TTS
        if (d.tts_url) {
          playTTS(d.tts_url);
        }
      } catch (e) {
        messages.value[lastIdx].content = "⚠️ " + e.message;
        setStatus("err", "出错了");
      }
    }

    // ---- 语音对话 ----
    let mediaRecorder = null;
    let audioChunks = [];

    async function toggleRecord() {
      if (isRecording.value) {
        stopRecord();
        return;
      }
      if (!navigator.mediaDevices?.getUserMedia) {
        micTip.value = "浏览器不支持录音";
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia(getMicConstraints());
        // 优先 wav，否则用默认格式（转码）
        const mime = MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
        mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
        audioChunks = [];
        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
        mediaRecorder.onstop = () => {
          stream.getTracks().forEach((t) => t.stop());
          sendAudio();
        };
        mediaRecorder.start();
        isRecording.value = true;
        micTip.value = "正在录音，点击停止";
      } catch (e) {
        micTip.value = "无法访问麦克风: " + e.message;
      }
    }

    function stopRecord() {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
      isRecording.value = false;
      micTip.value = "识别中...";
    }

    // 把任意格式音频转成 16k 单声道 WAV
    async function blobToWav16k(blob) {
      const arrayBuf = await blob.arrayBuffer();
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const audioBuf = await ctx.decodeAudioData(arrayBuf);
      const src = audioBuf.getChannelData(0);
      // 重采样到 16000
      const targetSr = 16000;
      const ratio = audioBuf.sampleRate / targetSr;
      const outLen = Math.round(src.length / ratio);
      const out = new Float32Array(outLen);
      for (let i = 0; i < outLen; i++) {
        const idx = Math.round(i * ratio);
        out[i] = src[Math.min(idx, src.length - 1)];
      }
      ctx.close();
      return encodeWav(out, targetSr);
    }

    function encodeWav(samples, sampleRate) {
      const buffer = new ArrayBuffer(44 + samples.length * 2);
      const view = new DataView(buffer);
      const writeStr = (off, str) => {
        for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
      };
      writeStr(0, "RIFF");
      view.setUint32(4, 36 + samples.length * 2, true);
      writeStr(8, "WAVE");
      writeStr(12, "fmt ");
      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);      // PCM
      view.setUint16(22, 1, true);      // mono
      view.setUint32(24, sampleRate, true);
      view.setUint32(28, sampleRate * 2, true);
      view.setUint16(32, 2, true);
      view.setUint16(34, 16, true);
      writeStr(36, "data");
      view.setUint32(40, samples.length * 2, true);
      let offset = 44;
      for (let i = 0; i < samples.length; i++) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
        offset += 2;
      }
      return new Blob([buffer], { type: "audio/wav" });
    }

    async function sendAudio() {
      if (audioChunks.length === 0) return;
      const rawBlob = new Blob(audioChunks);
      micTip.value = "转换音频...";
      let wavBlob;
      try {
        wavBlob = await blobToWav16k(rawBlob);
      } catch (e) {
        micTip.value = "音频转换失败: " + e.message;
        return;
      }
      if (wavBlob.size < 1000) {
        micTip.value = "录音太短";
        return;
      }
      const form = new FormData();
      form.append("file", wavBlob, "voice.wav");
      addMsg("user", "🎤 语音输入...");
      addMsg("assistant", "");
      setStatus("busy", "识别中...");
      const lastIdx = messages.value.length - 1;
      try {
        const r = await fetch("/api/audio", { method: "POST", body: form });
        const d = await r.json();
        if (d.error) throw new Error(d.error);
        // 更新用户消息为识别文本
        messages.value[lastIdx - 1].content = "🎤 你说：" + (d.user_text || "(未识别)");
        messages.value[lastIdx].content = d.reply;
        messages.value[lastIdx].tools = d.tool_calls || [];
        micTip.value = "";
        setStatus("ok", "就绪");
        // 播放 TTS（mp3 或 wav）
        if (d.tts_url) {
          playTTS(d.tts_url);
        }
      } catch (e) {
        messages.value[lastIdx].content = "⚠️ " + e.message;
        micTip.value = "";
        setStatus("err", "出错了");
      }
    }

    async function playTTS(url) {
      // 后台 TTS 异步生成，重试等待文件就绪
      for (let i = 0; i < 6; i++) {
        try {
          const audio = new Audio(url);
          await audio.play();
          return;
        } catch (e) {
          await new Promise((r) => setTimeout(r, 1500));
        }
      }
    }

    // ---- 重置 ----
    async function resetChat() {
      messages.value = [];
      try {
        await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: "", reset: true }),
        });
      } catch (e) {}
      setStatus("ok", "已重置");
    }

    // ---- 初始化 ----
    healthCheck();
    setInterval(healthCheck, 15000);
    refreshDevices();

    addMsg("system", "👋 你好！我是本地语音助手。\n可以直接打字，或点击麦克风说话。\n支持：天气查询 / 网络搜索 / 定时提醒");

    return {
      messages, input, status, statusText,
      isRecording, micTip,
      micDevices, selectedDevice, refreshDevices,
      sendText, toggleRecord, resetChat,
    };
  },
}).mount("#app");
