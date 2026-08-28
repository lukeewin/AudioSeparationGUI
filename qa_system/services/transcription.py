from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable, List

import ffmpeg
import psutil
import torch
from funasr import AutoModel

from qa_system.services.diarization import Diarizer, SpeakerSegment


@dataclass
class TranscriptResult:
    source_file: str
    full_text: str
    segments: List[SpeakerSegment]


class OfflineTranscriptionService:
    def __init__(self, model_root: Path | None = None, diarization_strategy: str = "campp") -> None:
        home = Path.home()
        base = model_root or home / ".cache" / "modelscope" / "hub" / "models" / "iic"
        self.model = AutoModel(
            model=str(base / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"),
            model_revision="v2.0.4",
            vad_model=str(base / "speech_fsmn_vad_zh-cn-16k-common-pytorch"),
            vad_model_revision="v2.0.4",
            punc_model=str(base / "punc_ct-transformer_zh-cn-common-vocab272727-pytorch"),
            punc_model_revision="v2.0.4",
            spk_model=str(base / "speech_campplus_sv_zh-cn_16k-common"),
            spk_model_revision="v2.0.4",
            ngpu=1 if torch.cuda.is_available() else 0,
            ncpu=psutil.cpu_count(),
            disable_pbar=True,
            disable_log=True,
            disable_update=True,
        )
        self.diarizer = Diarizer(strategy=diarization_strategy)

    @staticmethod
    def _to_time(ms: int) -> str:
        d = timedelta(milliseconds=ms)
        return f"{d.seconds // 3600:02d}:{(d.seconds // 60) % 60:02d}:{d.seconds % 60:02d}.{d.microseconds // 1000:03d}"

    @staticmethod
    def _iter_audio_files(paths: Iterable[str]) -> Iterable[str]:
        support_ext = {".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac", ".wma", ".aif", ".mp4", ".avi", ".mov", ".mkv"}
        for path in paths:
            p = Path(path)
            if p.is_file() and p.suffix.lower() in support_ext:
                yield str(p)
            if p.is_dir():
                for child in p.rglob("*"):
                    if child.is_file() and child.suffix.lower() in support_ext:
                        yield str(child)

    def transcribe_batch(self, source_paths: Iterable[str], merge_threshold_chars: int = 12, hotwords: str = "") -> List[TranscriptResult]:
        results: List[TranscriptResult] = []
        for audio in self._iter_audio_files(source_paths):
            audio_bytes, _ = (
                ffmpeg.input(audio, threads=0)
                .output("-", format="wav", acodec="pcm_s16le", ac=1, ar=16000)
                .run(cmd=["ffmpeg", "-nostdin"], capture_stdout=True, capture_stderr=True)
            )

            infer_result = self.model.generate(
                input=audio_bytes,
                batch_size_s=300,
                is_final=True,
                sentence_timestamp=True,
                hotword=hotwords,
            )[0]

            sentence_info = infer_result.get("sentence_info", [])
            if self.diarizer.strategy == "pyannote":
                segments = self.diarizer.diarize_with_pyannote(audio)
            else:
                segments = self.diarizer.diarize_with_funasr(sentence_info)
            segments = self.diarizer.merge_adjacent(segments, merge_threshold_chars)
            results.append(
                TranscriptResult(
                    source_file=audio,
                    full_text=infer_result.get("text", ""),
                    segments=segments,
                )
            )
        return results

    @classmethod
    def render_dialogue_log(cls, transcript: TranscriptResult) -> str:
        rows = [f"# 文件: {os.path.basename(transcript.source_file)}"]
        for seg in transcript.segments:
            start = cls._to_time(seg.start_ms)
            end = cls._to_time(seg.end_ms)
            rows.append(f"{seg.speaker} [{start} --> {end}]：{seg.text}")
        return "\n".join(rows)
