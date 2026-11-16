""".RPP 构建：契约 §5 冻结模板。"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

_SAFE_NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")


@dataclass
class RppItem:
    path: str | os.PathLike
    length: float


def _fmt_float(value: float) -> str:
    return repr(float(value))


def _new_guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def _quote_rpp_string(value: str) -> str:
    if any(ch not in _SAFE_NAME_CHARS for ch in value):
        return f'"{value}"'
    return value


def _rel_path(audio_path, rpp_dir) -> str:
    try:
        return os.path.relpath(os.path.abspath(audio_path), os.path.abspath(rpp_dir)).replace("\\", "/")
    except ValueError as exc:
        raise ValueError(f"无法生成相对路径：音频与保存位置不在同一磁盘（{exc}）") from exc


def _source_block_lines(suffix: str, rel: str) -> list[str]:
    file_line = f'        FILE "{rel}"'
    if suffix in (".wav", ".aiff", ".aif"):
        return ["      <SOURCE WAVE", file_line]
    if suffix == ".flac":
        return ["      <SOURCE FLAC", file_line]
    if suffix == ".mp3":
        return ["      <SOURCE MP3", f"{file_line} 1"]
    if suffix in (".m4a", ".m4r", ".mp4"):
        return ["      <SOURCE VIDEO", "        FLIP 0 1", file_line]
    if suffix in (".ogg", ".oga"):
        return ["      <SOURCE VORBIS", file_line]
    if suffix == ".opus":
        return ["      <SOURCE OPUS", file_line]
    return ["      <SOURCE WAVE", file_line]


def build_rpp(items, rpp_dir, track_name="PGM", timestamp=None, sample_rate: int = 44100) -> str:
    """构建 .RPP 文本（UTF-8 字符串，LF 行尾）。items 为 RppItem 可迭代对象。"""
    if timestamp is None:
        timestamp = int(time.time())

    items = list(items)
    positions: list[float] = []
    pos = 0.0
    for item in items:
        positions.append(pos)
        pos += float(item.length)

    track_guid = _new_guid()
    trackid = _new_guid()

    lines: list[str] = [
        f'<REAPER_PROJECT 0.1 "7.0" {int(timestamp)}',
        "  RIPPLE 0",
        "  GROUPOVERRIDE 0 0 0",
        "  AUTOXFADE 1",
        "  ENVATTACH 1",
        "  POOLEDENVATTACH 0",
        "  MIXERUIFLAGS 11 48",
        "  PEAKGAIN 1",
        "  FEEDBACK 0",
        "  PANLAW 1",
        "  PROJOFFS 0 0 0",
        "  MAXPROJLEN 0 600",
        "  GRID 3199 8 1 8 1 0 0 0",
        "  TIMEMODE 1 5 -1 30 0 0 -1",
        "  PANMODE 3",
        "  CURSOR 0",
        "  ZOOM 100 0 0",
        "  VZOOMEX 6 0",
        "  USE_REC_CFG 0",
        "  RECMODE 1",
        "  SMPTESYNC 0 30 100 40 1000 300 0 0 1 0 0",
        "  LOOP 0",
        "  LOOPGRAN 0 4",
        '  RECORD_PATH "" ""',
        f"  SAMPLERATE {int(sample_rate)} 0 0",
        "  LOCK 0",
        "  GLOBAL_AUTO -1",
        "  TEMPO 120 4 4",
        "  PLAYRATE 1 0 0.25 4",
        "  SELECTION 0 0",
        "  SELECTION2 0 0",
        "  MASTERAUTOMODE 0",
        "  MASTERTRACKHEIGHT 0 0",
        "  MASTERPEAKCOL 16576",
        "  MASTERMUTESOLO 0",
        "  MASTERTRACKVIEW 0 0.6667 0.5 0.5 0 0 0 0 0 0 -1 -1 0 0",
        "  MASTERHWOUT 0 0 1 0 0 0 0 -1",
        "  MASTER_NCH 2 2",
        "  MASTER_VOLUME 1 0 -1 -1 1",
        "  MASTER_FX 1",
        "  MASTER_SEL 0",
    ]

    for idx, item in enumerate(items, start=1):
        start = positions[idx - 1]
        end = start + float(item.length)
        region_name = Path(item.path).stem
        lines.append(f'  MARKER {idx} {_fmt_float(start)} "{region_name}" 1 0 1 B {_new_guid()} 0')
        lines.append(f'  MARKER {idx} {_fmt_float(end)} "" 1')

    lines.append(f"  <TRACK {track_guid}")
    lines.extend([
        f"    NAME {_quote_rpp_string(track_name)}",
        "    PEAKCOL 16576",
        "    BEAT -1",
        "    AUTOMODE 0",
        "    VOLPAN 1 0 -1 -1 1",
        "    MUTESOLO 0 0 0",
        "    IPHASE 0",
        "    PLAYOFFS 0 1",
        "    ISBUS 0 0",
        "    BUSCOMP 0 0 0 0 0",
        "    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0",
        "    FREEMODE 0",
        "    SEL 0",
        "    REC 0 0 1 0 0 0 0",
        "    VU 2",
        "    TRACKHEIGHT 0 0 0",
        "    INQ 0 0 0 0.5 100 0 0 100",
        "    NCHAN 2",
        "    FX 0",
        f"    TRACKID {trackid}",
        "    PERF 0",
        "    MIDIOUT -1",
        "    MAINSEND 1 0",
    ])

    for n, item in enumerate(items, start=1):
        rel = _rel_path(item.path, rpp_dir)
        lines.extend([
            "    <ITEM",
            f"      POSITION {_fmt_float(positions[n - 1])}",
            "      SNAPOFFS 0",
            f"      LENGTH {_fmt_float(item.length)}",
            "      LOOP 1",
            "      ALLTAKES 0",
            "      FADEIN 1 0 0 1 0 0 0",
            "      FADEOUT 1 0 0 1 0 0 0",
            "      MUTE 0 0",
            "      SEL 0",
            f"      IGUID {_new_guid()}",
            f"      IID {n}",
            f"      NAME {_quote_rpp_string(Path(item.path).name)}",
            "      VOLPAN 1 0 1 -1",
            "      SOFFS 0",
            "      PLAYRATE 1 1 0 -1 0 0.0025",
            "      CHANMODE 0",
            f"      GUID {_new_guid()}",
            *_source_block_lines(Path(item.path).suffix.lower(), rel),
            "      >",
            "    >",
        ])

    lines.append("  >")
    lines.append(">")
    return "\n".join(lines) + "\n"


def write_rpp(path, content: str) -> None:
    """以 UTF-8、LF 行尾写入 .RPP 文件。"""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
