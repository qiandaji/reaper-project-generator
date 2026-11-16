"""音频时长：mutagen（契约 §4）。"""
from __future__ import annotations

from pathlib import Path

from mutagen import File as MutagenFile


def get_duration(path) -> float:
    """返回音频时长（秒，float）。解析失败抛 ValueError。"""
    name = Path(path).name
    audio = MutagenFile(str(path))
    if audio is None or audio.info is None:
        raise ValueError(f"无法读取音频信息：{name}")
    length = getattr(audio.info, "length", None)
    if length is None:
        raise ValueError(f"无法读取时长：{name}")
    return float(length)


def get_sample_rate(path) -> int:
    """返回音频采样率（Hz，int）。解析失败抛 ValueError。"""
    name = Path(path).name
    audio = MutagenFile(str(path))
    if audio is None or audio.info is None:
        raise ValueError(f"无法读取采样率：{name}")
    sample_rate = getattr(audio.info, "sample_rate", None)
    if sample_rate is None:
        raise ValueError(f"无法读取采样率：{name}")
    return int(sample_rate)
