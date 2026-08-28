from __future__ import annotations

import threading
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from qa_system.services.transcription import OfflineTranscriptionService

mcp = FastMCP("qa-system-asr")
_service_lock = threading.Lock()
_service = OfflineTranscriptionService()


def _extract_path_from_prompt(prompt: str) -> str:
    quote_chars = ['"', '“', '”', "'", '‘', '’']
    for q in quote_chars:
        if q in prompt:
            parts = prompt.split(q)
            if len(parts) >= 3 and parts[1].strip():
                return parts[1].strip()

    for token in prompt.split():
        if token.startswith(("/", "./", "../")):
            return token.strip("，。,.!！")

    return prompt.strip()


@mcp.tool()
def transcribe_audio_to_speaker_log(
    prompt: str,
    diarization: str = "campp",
    merge_threshold_chars: int = 12,
    hotwords: str = "",
) -> str:
    """根据自然语言 prompt 转写本地录音，并返回说话人日志文本。"""
    audio_path = _extract_path_from_prompt(prompt)
    path = Path(audio_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"音频文件不存在或不是文件: {path}")

    with _service_lock:
        _service.diarizer.strategy = diarization
        results = _service.transcribe_batch(
            source_paths=[str(path)],
            merge_threshold_chars=merge_threshold_chars,
            hotwords=hotwords,
        )

    if not results:
        raise RuntimeError(f"未识别到可处理的音频文件: {path}")

    return _service.render_dialogue_log(results[0])


if __name__ == "__main__":
    mcp.run()
