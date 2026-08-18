"""大模型对话（LLM）：transformers + bitsandbytes 4bit + Qwen3-8B。

支持工具调用（M4）：Qwen3 原生 function calling（Hermes-2-Pro 风格，
<tool_call>{"name": ..., "arguments": ...}</tool_call>）。
"""
import json
import re

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextStreamer,
)
import torch

from .config import (
    LLM_MODEL_ID,
    LLM_QUANT_BITS,
    LLM_MAX_NEW_TOKENS,
    LLM_TEMPERATURE,
    SYSTEM_PROMPT,
    DEVICE,
)


class ChatModel:
    """本地 Qwen3 对话模型（4bit 量化），支持工具调用。"""

    def __init__(
        self,
        model_id: str = LLM_MODEL_ID,
        device: str = DEVICE,
        quant_bits: int = LLM_QUANT_BITS,
    ):
        print(f"[llm] loading {model_id} ({quant_bits}bit, {device}) ...")
        if device == "cuda" and quant_bits in (4, 8):
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=(quant_bits == 4),
                load_in_8bit=(quant_bits == 8),
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        else:
            bnb_config = None

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=True, local_files_only=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True,
            local_files_only=True,
        )
        self.history: list[dict] = []
        print("[llm] ready")

    def reset(self):
        self.history = []

    def _prepare_messages(self, messages: list[dict], tools: list[dict] | None) -> str:
        """按 Qwen3 chat_template 构造提示词（关闭思考模式）。"""
        msgs = []
        for m in messages:
            m = dict(m)
            if m["role"] == "system":
                m["content"] = m["content"] + "\n请直接给出最终回答，不要输出思考过程。"
            msgs.append(m)
        kwargs = dict(
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        if tools:
            kwargs["tools"] = tools
        return self.tokenizer.apply_chat_template(msgs, **kwargs)

    def _generate(self, text: str, stream: bool = False) -> str:
        """生成回复文本。"""
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        streamer = None
        if stream:
            streamer = TextStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=LLM_MAX_NEW_TOKENS,
                temperature=LLM_TEMPERATURE,
                top_p=0.9,
                repetition_penalty=1.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                streamer=streamer,
            )
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    @staticmethod
    def parse_tool_calls(text: str) -> list[dict]:
        """从生成文本中解析工具调用。

        返回 [{name, arguments(dict)}]；无工具调用返回 []。
        """
        calls = []
        pattern = re.compile(
            r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.S
        )
        for m in pattern.finditer(text):
            raw = m.group(1)
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            name = obj.get("name", "")
            args = obj.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if name:
                calls.append({"name": name, "arguments": args})
        return calls

    def chat(self, user_text: str, stream: bool = False) -> str:
        """单轮对话（无工具）。返回助手回复文字。"""
        if not self.history:
            self.history.append({"role": "system", "content": SYSTEM_PROMPT})
        self.history.append({"role": "user", "content": user_text})
        text = self._prepare_messages(self.history, tools=None)
        reply = self._generate(text, stream=stream)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def chat_with_tools(
        self,
        user_text: str,
        tools: list[dict],
        tool_executor,
        max_turns: int = 4,
        stream: bool = False,
    ) -> str:
        """带工具调用的对话（自动执行工具并回填结果）。

        tools: [{type:"function", function:{name, description, parameters}}]
        tool_executor: callable(name, arguments) -> str（工具执行结果文本）
        返回最终助手回复。
        """
        if not self.history:
            self.history.append({"role": "system", "content": SYSTEM_PROMPT})
        self.history.append({"role": "user", "content": user_text})

        for _ in range(max_turns):
            text = self._prepare_messages(self.history, tools=tools)
            reply = self._generate(text, stream=stream)
            calls = self.parse_tool_calls(reply)
            if not calls:
                # 无工具调用：最终回复
                self.history.append({"role": "assistant", "content": reply})
                return reply
            # 有工具调用：记录 assistant 消息（tool_calls），执行后回填
            self.history.append(
                {
                    "role": "assistant",
                    "content": reply,
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": json.dumps(c["arguments"], ensure_ascii=False),
                            },
                        }
                        for c in calls
                    ],
                }
            )
            for c in calls:
                try:
                    result = tool_executor(c["name"], c["arguments"])
                except Exception as e:
                    result = f"工具执行失败：{e}"
                print(f"[tools] {c['name']}({c['arguments']}) -> {result[:80]}...")
                self.history.append(
                    {
                        "role": "tool",
                        "content": f"<tool_response>\n{result}\n</tool_response>",
                        "tool_call_id": c["name"],
                        "name": c["name"],
                    }
                )
        # 超过轮数：兜底再生成一次
        text = self._prepare_messages(self.history, tools=None)
        reply = self._generate(text, stream=stream)
        self.history.append({"role": "assistant", "content": reply})
        return reply


_inst = None


def get_chat_model() -> ChatModel:
    global _inst
    if _inst is None:
        _inst = ChatModel()
    return _inst
