/** 音频工具：把任意格式录音转成 16kHz 单声道 WAV */

/** 解码任意音频并转成 16k 单声道 WAV Blob */
export async function blobToWav16k(blob: Blob): Promise<Blob> {
  const arrayBuf = await blob.arrayBuffer();
  const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
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

/** 编码 PCM 为 WAV（16bit PCM 单声道） */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeStr = (off: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(off + i, str.charCodeAt(i));
    }
  };
  writeStr(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, samples.length * 2, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: "audio/wav" });
}
