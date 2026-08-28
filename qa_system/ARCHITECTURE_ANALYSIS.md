# qa_system 代码结构与链路分析

## 1. UNDERSTAND（理解）
项目 `qa_system` 的核心问题是：
- 在**本地离线**条件下，把上传的录音文件进行 ASR 转写；
- 结合说话人分离能力，把文本按说话人切分；
- 以可质检的日志格式输出，支持后续销售/客户话术分析。

它本质上是一个“Web 任务壳 + 离线语音处理引擎”的组合系统。

## 2. ANALYZE（分析）

### 2.1 分层结构
- 接入层（HTTP + 页面）：`qa_system/app.py`、`templates/index.html`、`static/script.js`
- 领域服务层（转写编排）：`services/transcription.py`
- 说话人策略层（可替换实现）：`services/diarization.py`
- 测试层：`tests/test_diarization.py`

### 2.2 关键对象
- `OfflineTranscriptionService`
  - 负责模型初始化（FunASR `AutoModel`）
  - 批处理音频、调用 ffmpeg 统一采样、执行转写
  - 调用 `Diarizer` 进行 speaker 归因与段落合并
- `Diarizer`
  - `campp`：基于 FunASR 返回的 `sentence_info` 映射
  - `pyannote`：保留扩展入口，当前抛出 `NotImplementedError`
- `jobs`（内存字典）
  - job 状态机：`running -> done/failed`
  - 结果缓存与轮询查询

### 2.3 外部依赖角色
- `FastAPI`：接口与模板渲染
- `ffmpeg-python`：音频预处理（转 16k 单声道 wav）
- `funasr` + `torch`：离线转写与 speaker 信息生成
- `psutil`：CPU 核数探测

## 3. REASON（推理）

### 3.1 端到端调用链（主链路）
1. 前端提交表单（多文件 + diarization + merge_threshold + hotwords）到 `POST /api/jobs`。
2. 后端保存上传文件到 `uploads/<job_id>/`，生成 job 记录并异步投递线程池。
3. 后台线程调用 `service.transcribe_batch(...)`：
   - 遍历可识别音/视频文件；
   - 每个文件先经 ffmpeg 统一解码；
   - 调用 FunASR `generate` 获取 `text` 和 `sentence_info`；
   - 根据策略分支：
     - `campp`：从 `sentence_info` 直接映射 speaker 段；
     - `pyannote`：当前未落地，会报错；
   - 对短句相邻同 speaker 段做合并；
   - 产出 `TranscriptResult`。
4. 后端将每个文件转成可读日志（`speaker + 时间戳 + 文本`），写入 `results/<job_id>.txt`。
5. 前端轮询 `GET /api/jobs/{job_id}`，直到 `done`/`failed`，渲染结果文本。

### 3.2 数据流（字段级）
- 输入：浏览器 `multipart/form-data`
  - `files[]`
  - `diarization`
  - `merge_threshold_chars`
  - `hotwords`
- 中间：`jobs[job_id]`
  - 初始：`status=running`
  - 成功：`status=done, result, files`
  - 失败：`status=failed, error`
- 模型中间态：
  - `infer_result.text`
  - `infer_result.sentence_info[]`（含 `spk/start/end/text`）
- 输出：
  - API JSON（轮询态）
  - 落盘文本日志（质检可读）

### 3.3 当前工程权衡
- 优点：
  - 结构清晰、接口简洁、离线可运行；
  - speaker 策略做了抽象，有后续扩展位；
  - 前后端耦合低（纯 JSON 轮询）。
- 风险/限制：
  - `jobs` 在内存中，进程重启丢失任务；
  - 线程池仅 2 worker，吞吐受限；
  - `service.diarizer.strategy` 在并发下会被全局覆写（竞态风险）；
  - `pyannote` 分支尚未实现；
  - 缺少端到端集成测试与异常可观测性（日志/指标）。

## 4. SYNTHESIZE（综合）

### 4.1 当前应用结构可以理解为
- **控制平面**：FastAPI + job 状态管理 + 页面轮询
- **数据平面**：ffmpeg 预处理 + FunASR 推理 + diarizer 后处理
- **输出平面**：文本日志与 JSON 状态

### 4.2 建议的工程化增强路径（按优先级）
1. 并发安全：将 `diarization` 作为 `transcribe_batch` 的入参，而不是修改共享 service 实例属性。
2. 任务持久化：把 `jobs` 落到 SQLite/Redis，支持重启恢复。
3. 任务队列化：引入后台队列（RQ/Celery）替代进程内线程池。
4. 可观测性：增加结构化日志、任务耗时、失败原因分类。
5. pyannote 落地：补齐 token、模型缓存与 pipeline 初始化。

## 5. CONCLUDE（总结）
`qa_system` 已具备一个可用的离线语音质检原型骨架：
- 上传 -> 异步转写 -> speaker 分离 -> 日志输出闭环完整；
- 代码边界（Web / 转写 / diarization）基本合理；
- 后续应优先补“并发安全 + 持久化 + pyannote 实现”，即可从原型走向稳定可运维版本。
