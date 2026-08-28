# QA System 架构与数据链路分析

## 1. 系统定位

`qa_system` 是一个本地离线语音质检 Web 原型：
- 后端用 FastAPI 提供上传、异步任务、结果轮询接口。
- 核心能力是 FunASR 离线 ASR + 说话人分离。
- 前端是单页表单 + 轮询状态，输出说话人日志。

## 2. 代码结构

- `qa_system/app.py`：应用入口、接口定义、任务调度、结果落盘与状态管理。
- `qa_system/services/transcription.py`：离线转写总流程（音频预处理、模型推理、说话人分离策略选择、分段合并、日志格式化）。
- `qa_system/services/diarization.py`：说话人分离抽象层，当前主路径为 FunASR 句级说话人标签映射，预留 pyannote 扩展。
- `qa_system/templates/index.html`：上传与参数输入页面。
- `qa_system/static/script.js`：前端提交任务 + 轮询 `/api/jobs/{job_id}`。
- `qa_system/tests/test_diarization.py`：验证 diarizer 字段映射与合并逻辑。

## 3. 核心调用链路

1. 浏览器提交表单到 `POST /api/jobs`。
2. 后端将上传文件保存到 `uploads/<job_id>/`。
3. 后端在内存 `jobs[job_id]` 写入 `running` 状态，并将实际处理丢给线程池。
4. 后台线程调用 `OfflineTranscriptionService.transcribe_batch()`：
   - 扫描有效音/视频文件；
   - ffmpeg 转成单声道 16k WAV 字节；
   - 调用 FunASR `generate()` 返回文本与句级时间戳/说话人信息；
   - 根据策略做 diarization（campp / pyannote）；
   - 做相邻同 speaker 短句合并；
   - 产出 `TranscriptResult`。
5. 后端把每个文件渲染为 `speaker + 时间戳 + 文本` 日志，写入 `results/<job_id>.txt`。
6. 内存状态更新为 `done`（或 `failed`）。
7. 前端轮询 `GET /api/jobs/{job_id}`，拿到结果并展示。

## 4. 数据流转（输入 -> 中间态 -> 输出）

### 4.1 输入层

- 文件输入：`files`（多文件）
- 参数输入：
  - `diarization`（`campp` / `pyannote`）
  - `merge_threshold_chars`（相邻同 speaker 合并阈值）
  - `hotwords`（ASR 热词）

### 4.2 处理中间态

- 文件落盘：`uploads/<job_id>/<filename>`
- 状态内存：`jobs[job_id] = {status, created_at, ...}`
- 音频中间表示：ffmpeg 输出 WAV bytes（单声道/16k）
- 模型中间结果：
  - `infer_result["text"]`
  - `infer_result["sentence_info"]`（包含 `spk/start/end/text`）
- 领域对象：`SpeakerSegment`、`TranscriptResult`

### 4.3 输出层

- 文本文件：`results/<job_id>.txt`
- API 输出：
  - 创建任务返回 `job_id`
  - 查询任务返回 `running/done/failed` + 结果或错误
- 页面展示：任务状态 JSON + 说话人日志文本

## 5. qa_system 的关键设计点

- **离线优先**：ASR 主链路不依赖在线服务，模型从本地缓存加载。
- **策略解耦**：说话人分离通过 `Diarizer` 统一接口封装，默认 CAM++，可切 pyannote。
- **异步体验**：HTTP 接口快速返回 `job_id`，长任务在线程池执行，前端轮询。
- **可解释产物**：输出按 speaker + 时间轴组织，便于人工质检或后处理。

## 6. 当前限制与工程风险

- `jobs` 使用进程内字典，重启丢失、无法多实例共享。
- 线程任务数量固定（`max_workers=2`），高并发下排队明显。
- `service.diarizer.strategy` 在共享单例上被请求动态修改，存在并发串扰风险。
- pyannote 分支目前抛 `NotImplementedError`，前端可选但不可用。
- 文件读写与任务结果没有生命周期清理策略（磁盘增长风险）。

## 7. 建议的演进方向

1. 任务状态迁移到持久化存储（SQLite/Redis + 队列）。
2. 每个任务独立实例化转写服务或把策略作为函数参数透传，避免共享状态。
3. 对 pyannote 选项做能力探测，不可用时在前端禁用并给出提示。
4. 增加任务取消、超时、清理与审计日志。
5. 增加端到端测试（上传 -> 完成 -> 结果格式断言）。
