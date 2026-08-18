"""全局配置：路径、设备、模型参数。"""
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent

# 模型目录
MODELS_DIR = ROOT / "models"
SENSEVOICE_DIR = MODELS_DIR / "SenseVoiceSmall"
QWEN_DIR = MODELS_DIR / "Qwen3-8B"
COSYVOICE_DIR = MODELS_DIR / "CosyVoice2-0.5B"

# 输出目录
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 设备
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[config] device = {DEVICE}")

# LLM 参数
LLM_MODEL_ID = str(QWEN_DIR)          # 本地 safetensors 目录
LLM_QUANT_BITS = 4                    # bitsandbytes 4bit 量化
LLM_MAX_NEW_TOKENS = 512
LLM_TEMPERATURE = 0.7

# 系统提示词（陪伴对话人设）
SYSTEM_PROMPT = (
    "你是一个温暖贴心的中文语音助手，名叫小助手。"
    "说话自然、简洁、口语化，像朋友聊天一样，不要用markdown格式和列表。"
    "回答尽量控制在100字以内，因为用户是通过语音和你交流的。"
)

# STT 参数
STT_MODEL_DIR = str(SENSEVOICE_DIR)
STT_SAMPLE_RATE = 16000

# M2 参数
VAD_MODEL_DIR = str(MODELS_DIR / "fsmn-vad")
SAMPLE_RATE = 16000            # 全链路统一采样率（VAD/STT 都是 16k）
VAD_CHUNK_SECONDS = 0.1        # VAD 分块时长（100ms）
VAD_MIN_SPEECH_MS = 200        # 小于该时长视为噪声
VAD_SILENCE_MS = 500           # 语音结束后静音多久判定为句子结束
WAKE_WORDS = ["小助手", "小助", "你好小助"]  # 唤醒词列表
LISTEN_TIMEOUT = 10            # 唤醒后等待指令的超时（秒）
MAX_UTTERANCE_SECONDS = 30     # 单句话最长时长

# TTS 参数
TTS_MODEL_DIR = str(COSYVOICE_DIR)
TTS_SAMPLE_RATE = 24000
TTS_SPEED = 1.0
