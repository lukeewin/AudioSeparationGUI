# qa_system 封装为 MCP Tool 的设计方案

## 1. 目标
把现有离线 ASR + 说话人分离服务封装成一个 MCP Tool，供外部 Agent/LLM 通过自然语言触发：

- 输入示例：`帮我转录一下录音文件“/data/audios/call_001.wav”`
- 输出：带 speaker 标签与时间戳的说话人日志文本

## 2. 工具设计

### 2.1 Tool 名称
- `transcribe_audio_to_speaker_log`

### 2.2 输入契约
- `prompt: str`（必填）：自然语言指令，内部自动提取音频路径
- `diarization: str = "campp"`
- `merge_threshold_chars: int = 12`
- `hotwords: str = ""`

### 2.3 输出契约
- `str`：
  - `# 文件: xxx.wav`
  - `speaker1 [00:00:00.000 --> 00:00:01.230]：...`

## 3. 处理链路
1. MCP Agent 调用 tool，传入自然语言 prompt。
2. Tool 从 prompt 中提取文件路径（优先引号内容，其次绝对/相对路径 token）。
3. 校验路径有效性。
4. 调用 `OfflineTranscriptionService.transcribe_batch([path], ...)`。
5. 用 `render_dialogue_log` 生成最终文本并返回给 Agent/LLM。

## 4. 当前实现说明
- 代码文件：`qa_system/mcp_tool_server.py`
- 使用 `FastMCP` 注册 tool。
- 采用单例 `OfflineTranscriptionService` + 互斥锁，避免并发下策略切换冲突。

## 5. 工程化建议
1. 安全：新增路径白名单（例如仅允许 `/data/uploads`）。
2. 稳定性：把 diarization 策略改为调用级参数，避免修改共享对象状态。
3. 可扩展：新增批量工具 `transcribe_batch_to_speaker_logs(paths: list[str])`。
4. 结果结构化：返回 JSON（文件、段落数组、耗时）并附带纯文本版本。

## 6. 与现有 Web 服务关系
- Web 版（FastAPI）用于人工上传与可视化轮询。
- MCP 版用于程序化调用（Agent/LLM）。
- 两者复用同一套核心服务层（`services/transcription.py` + `services/diarization.py`）。
