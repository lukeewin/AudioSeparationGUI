from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib.util import find_spec
from typing import List


@dataclass
class SpeakerSegment:
    speaker: str
    start_ms: int
    end_ms: int
    text: str


class Diarizer:
    """Diarization abstraction supporting FunASR CAM++ first, then pyannote."""

    def __init__(self, strategy: str = "campp") -> None:
        self.strategy = strategy

    def diarize_with_funasr(self, sentence_info: list[dict]) -> List[SpeakerSegment]:
        segments: List[SpeakerSegment] = []
        for sentence in sentence_info:
            segments.append(
                SpeakerSegment(
                    speaker=f"speaker{sentence['spk']}",
                    start_ms=int(sentence["start"]),
                    end_ms=int(sentence["end"]),
                    text=sentence["text"],
                )
            )
        return segments

    def diarize_with_pyannote(self, audio_path: str) -> List[SpeakerSegment]:
        if find_spec("pyannote.audio") is None:
            raise RuntimeError("pyannote.audio 未安装，无法使用 pyannote 方案")

        pipeline_module = import_module("pyannote.audio")
        Pipeline = getattr(pipeline_module, "Pipeline")

        raise NotImplementedError(
            "pyannote 方案需要 HuggingFace Token 与模型配置，请在生产环境接入后启用。"
            f"当前输入文件: {audio_path}"
        )

    def merge_adjacent(self, segments: List[SpeakerSegment], merge_threshold_chars: int = 12) -> List[SpeakerSegment]:
        if not segments:
            return []

        merged = [segments[0]]
        for current in segments[1:]:
            previous = merged[-1]
            if current.speaker == previous.speaker and len(previous.text) < merge_threshold_chars:
                previous.text += current.text
                previous.end_ms = current.end_ms
            else:
                merged.append(current)
        return merged
