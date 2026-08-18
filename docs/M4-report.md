# 语音助手 Agent — M4 完成报告

> 日期：2026-08-16
> 状态：✅ M4 "天气/搜索/提醒工具调用"已完成

## 能力与实现

### 1. 天气查询（`tools/weather.py`）
- **数据源**：Open-Meteo（免费、无需 API key、支持 HTTP）
- **流程**：城市名 → geocoding API（支持中文）→ 经纬度 → forecast API
- **返回**：当前天气（温度/湿度/风速）+ 未来 3 天预报（中文描述）
- 天气代码 WMO → 中文映射（晴/多云/雨/雪/雷暴等）

### 2. 网络搜索（`tools/search.py`）
- **数据源**：cn.bing.com（HTTP 可达；www.bing.com 302 到 cn.bing.com）
- **解析**：HTML 正则提取 `b_algo` 条目（标题/URL/摘要）
- 返回前 5 条格式化结果

### 3. 提醒（`tools/reminder.py`）
- **倒计时**：`add_after(minutes, text)`
- **定时**：`add_at(hour, minute, text)`（每天 HH:MM，过期自动排明天）
- **触发**：后台 daemon 线程每秒检查，到期调用 `on_trigger` 回调
- 支持列出/取消

### 4. LLM 工具调用（`llm.py` 重构）
- Qwen3-8B 原生 function calling（chat_template 支持 Hermes-2-Pro 风格）
- `parse_tool_calls`：正则解析 `<tool_call>{"name":..., "arguments":...}</tool_call>`
- `chat_with_tools`：多轮循环（LLM 生成 → 解析 → 执行 → 回填 tool_response → 再生成）
- 修复：`apply_chat_template` 位置参数、`torch_dtype`→`dtype`（transformers 5.15）

### 5. 工具注册表（`tools/registry.py`）
- 统一管理 schema + executor（新增工具只需注册一条）
- 全局提醒管理器单例

## 测试结果

| 测试 | 结果 |
|---|---|
| parse_tool_calls（5 组用例） | ✅ 全部通过 |
| 工具注册表（3 工具 + 未知工具） | ✅ 通过 |
| 天气工具独立调用 | ✅ 返回真实数据（北京 24.1°C 晴） |
| 搜索工具独立调用 | ✅ 返回真实结果（今日热榜等） |
| 提醒解析（倒计时/定时/中文时间） | ✅ 通过 |
| 提醒触发回调（含文本传递） | ✅ 修复确认 |
| **端到端：LLM→天气工具→回复** | ✅ "北京今天有小阵雨，记得带伞哦！" |
| **端到端：LLM→搜索工具→回复** | ✅ 返回搜索结果并总结 |
| CLI --chat 带工具 | ✅ 正常 |

## 端到端演示

```
用户: 北京今天天气怎么样？
[tools] get_weather({'city': '北京'}) -> 北京（中国）当前天气：晴，24.1°C...
助手: 北京今天有小阵雨，气温22.5到27.4°C，记得带伞哦！

用户: 帮我搜索一下今天的新闻热点
[tools] web_search({'query': '今天的新闻热点'}) -> 关于「今天的新闻热点」的搜索结果...
助手: 这些是关于今天新闻热点的相关信息，你可以看看哪些最感兴趣。
```

## 运行方式

```powershell
# 交互式对话（文字，支持工具）
.venv\Scripts\python -m voice_assistant --chat
# 例：北京天气 / 搜索今天的新闻 / 5分钟后提醒我喝水

# 唤醒词语音模式（同样支持工具）
.venv\Scripts\python -m voice_assistant --listen
```

## 已知限制

1. **搜索是 HTML 解析**（非官方 API），Bing 改版可能失效；必要时可换其他源
2. **提醒是进程内定时器**：程序退出后提醒消失，重启不恢复（持久化留待后续）
3. **"明天开会"等相对日期提醒**暂不支持解析（只支持 N 分钟后 / HH:MM / X 点）
4. **单轮工具调用耗时**：LLM 首轮生成约 30-60s（含思考），工具执行 <5s

## 下一步

- [ ] M3：安卓 PWA 手机端（WebSocket 音频流）
- [ ] M5：CosyVoice2 接入 + 音色克隆
- [ ] 优化：提醒持久化（重启恢复）、更多工具（计算器/翻译）
