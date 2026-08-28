# 金融销售电话质检系统（二次开发版）

该目录是基于原项目核心能力（FunASR 离线转写 + 说话人分离）构建的 Web 版质检原型，面向“电话下单录音质检”场景。

## 功能

1. 支持录音文件批量上传。
2. 支持说话人分离（默认 FunASR CAM++，并预留 pyannote 扩展位）。
3. 支持普通离线自动转写。
4. 输出说话人日志（speaker + 时间戳 + 文本），用于 sales/customer 角色分析。

## 启动

```bash
pip install fastapi uvicorn jinja2 python-multipart
# 以及原项目依赖
pip install -U funasr modelscope ffmpeg-python pydub torch psutil

uvicorn qa_system.app:app --host 0.0.0.0 --port 8000 --reload
```

浏览器访问：`http://127.0.0.1:8000`

## 架构

- `app.py`: Web 接口、任务调度、状态轮询。
- `services/transcription.py`: 离线转写主流程（FunASR + ffmpeg）。
- `services/diarization.py`: 说话人分离抽象层（CAM++ / pyannote）。
- `templates/ + static/`: 前端交互页面。

## pyannote 说明

当前代码中保留了 pyannote 接口抽象，但默认未启用完整 Pipeline 初始化。生产接入时请按你们私有环境增加 HuggingFace Token、模型与缓存策略。
