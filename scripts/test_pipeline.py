"""M1 全链路测试：真实语音 → STT → LLM（模型串行加载，节省显存）。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.stt import Recognizer, load_wav_as_float  # noqa: E402

t0 = time.time()
rec = Recognizer()
audio, sr = load_wav_as_float(r"D:\dsh\voice-assistant\output\real_speech.wav")
user_text = rec.transcribe((audio, sr))
print(f"[stt] -> {user_text}  ({(time.time()-t0):.1f}s)")

# 卸载 STT 模型，释放显存
import torch
import gc

del rec
gc.collect()
torch.cuda.empty_cache()
print("[mem] STT unloaded, free memory:", round(torch.cuda.mem_get_info()[0] / 1e9, 2), "GB")

from voice_assistant.llm import ChatModel  # noqa: E402

chat = ChatModel()
t1 = time.time()
reply = chat.chat(f'用户说："{user_text}"。请用一句话热情回应。', stream=False)
print(f"[llm] -> {reply}  ({(time.time()-t1):.1f}s)")
print(f"[total] {(time.time()-t0):.1f}s")
