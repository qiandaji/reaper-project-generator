"""收集与分组：文件模式 / 文件夹模式，自然排序（契约 §3）。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".aiff", ".aif", ".flac", ".mp3", ".m4a", ".ogg", ".oga"}

_DIGIT_RE = re.compile(r"(\d+)")


def is_audio(path: str | os.PathLike) -> bool:
    return Path(path).suffix.lower() in AUDIO_EXTENSIONS


def natural_key(name: str):
    """自然排序键：不区分大小写，数字按数值（01 < 2 < 10）。"""
    return [int(part) if part.isdigit() else part for part in _DIGIT_RE.split(name.lower())]


@dataclass
class Group:
    name: str
    files: list[Path] = field(default_factory=list)


@dataclass
class CollectResult:
    groups: list[Group] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)


def _sorted_by_name(files: list[Path]) -> list[Path]:
    return sorted(files, key=lambda p: natural_key(p.name))


def _skip_quote_files(files: list[Path]) -> tuple[list[Path], list[str]]:
    kept: list[Path] = []
    logs: list[str] = []
    for path in files:
        if '"' in path.name:
            logs.append(f"跳过（文件名含双引号）：{path.name}")
        else:
            kept.append(path)
    return kept, logs


def _common_parent_name(files: list[Path]) -> str:
    dirs = [os.path.dirname(os.path.abspath(path)) for path in files]
    try:
        common = os.path.commonpath(dirs)
    except ValueError:
        return "新工程"
    return os.path.basename(common) or "新工程"


def collect_from_files(paths) -> CollectResult:
    """文件模式：所选文件 = 一个分组，组名 = 公共父目录名（无公共目录时为「新工程」）。"""
    result = CollectResult()
    audio: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if not is_audio(path):
            result.logs.append(f"跳过（非支持格式）：{path.name}")
            continue
        audio.append(path)
    kept, quote_logs = _skip_quote_files(audio)
    result.logs.extend(quote_logs)
    if kept:
        result.groups.append(Group(name=_common_parent_name(kept), files=_sorted_by_name(kept)))
    return result


def collect_from_folder(folder) -> CollectResult:
    """文件夹模式：仅处理所选文件夹本身 + 其一级子文件夹（不无限递归）。"""
    result = CollectResult()
    root = Path(folder)

    def audio_files_in(directory: Path) -> list[Path]:
        return [p for p in directory.iterdir() if p.is_file() and is_audio(p)]

    top_files = _sorted_by_name(audio_files_in(root))
    kept, quote_logs = _skip_quote_files(top_files)
    result.logs.extend(quote_logs)
    if kept:
        result.groups.append(Group(name=root.name or "新工程", files=kept))

    subdirs = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: natural_key(p.name))
    for sub in subdirs:
        files = _sorted_by_name(audio_files_in(sub))
        kept, quote_logs = _skip_quote_files(files)
        result.logs.extend(quote_logs)
        if kept:
            result.groups.append(Group(name=sub.name, files=kept))

    result.groups.sort(key=lambda g: natural_key(g.name))
    return result
