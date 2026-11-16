# REAPER 工程生成工具

> ⚠️ **本项目完全通过 AI 生成**：全部需求分析、设计、代码、测试与文档均由 AI 辅助完成，无人工手写代码。使用前请自行检查并测试。

一个独立的 Python GUI（tkinter）小工具：把选中的音频文件（或文件夹）自动整理成 REAPER 工程（.RPP）——所有音频放在**同一条轨道**上、按文件名自然排序、首尾相接，并且每个音频单独建立**以文件名命名的 region**。在 Mac 和 Windows 上双击启动器即可使用，**无需打开 REAPER** 即可生成工程文件。

## 功能

- **文件模式**：多选音频文件 → 生成一个工程（分组名 = 公共父目录名）。
- **文件夹模式**：选择文件夹 → 顶层音频生成一个工程；每个含音频的一级子文件夹各生成一个工程（不无限递归）。
- 所有音频放在同一条轨道（轨道名 PGM）上，按文件名**自然排序**（01 < 2 < 10），首尾相接不重叠。
- 每个音频对应一个 ITEM 和一对 MARKER（region），region 名 = 文件名去扩展名。
- 用 mutagen 读取音频时长与采样率；.RPP 采用 UTF-8 编码、LF 行尾、相对路径引用音频。
- 按扩展名写入 REAPER 7.x 正确的 `<SOURCE` 标签（见下表），避免 FLAC/MP3/M4A 等格式静音问题。

## 支持格式与 SOURCE 标签

| 扩展名 | SOURCE 标签 | 说明 |
|---|---|---|
| .wav / .aiff / .aif | `<SOURCE WAVE` | |
| .flac | `<SOURCE FLAC` | |
| .mp3 | `<SOURCE MP3` | FILE 行尾追加 1 |
| .m4a / .m4r / .mp4 | `<SOURCE VIDEO` | 额外一行 `FLIP 0 1` |
| .ogg / .oga | `<SOURCE VORBIS` | |
| .opus | `<SOURCE OPUS` | |
| 其他后缀 | `<SOURCE WAVE` | 回退 |

> 该映射与 REAPER 7.82 自身保存的工程一致；硬编码 `<SOURCE WAVE` 会导致 FLAC 等格式加载为静音。

## 环境要求

- Python 3.10+
- 首次运行会自动创建 `.venv` 虚拟环境并安装 mutagen（联网）
- macOS / Windows 均可

## 安装与启动

### macOS

双击 `start_macos.command`（首次可能需右键 → 打开，确认允许运行）。脚本会自动创建 .venv、安装 mutagen 并启动图形界面。

或手动：

    cd 本目录
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python -m app

### Windows

双击 `start_windows.bat`。脚本会自动创建 .venv、安装 mutagen 并启动图形界面。

或手动：

    cd /d 本目录
    py -3 -m venv .venv
    .venvScriptspython -m pip install -r requirements.txt
    .venvScriptspython -m app

Windows 建议从 python.org 安装 Python 并勾选 “Add Python to PATH”。

## 使用步骤

1. 点击「选择文件…」多选音频，或点击「选择文件夹…」选择包含音频的文件夹。
2. 在中间列表确认分组（组名 + 文件数）。
3. 点击「生成工程」：
   - 单个分组：选择保存位置，默认预填音频所在目录，文件名默认 {组名}.rpp。
   - 多个分组：选择保存目录，每个分组自动生成 {组名}.rpp；同名文件会逐个询问是否覆盖。
4. 生成成功后：单工程会询问是否立即用系统默认方式打开；多工程会提示保存目录并打开该目录。
5. 跳过或失败的文件会显示在底部日志文本框。

## 注意事项

- **相对路径**：.RPP 内以「从 .RPP 所在目录到音频文件」的相对路径引用音频；生成后请保持工程与音频的相对位置不变，否则 REAPER 会提示找不到媒体。
- 文件名含双引号 `"` 的音频会被跳过（.RPP 字符串无法可靠转义）。
- 文件夹模式只处理所选文件夹本身和它的一级子文件夹。
- 时长读取失败的文件会被跳过并写日志；若所有分组都没有可用音频，则不生成工程。
- 音频与保存位置**不在同一磁盘**（仅 Windows 跨盘）时无法生成相对路径，该工程会被跳过并写日志。

## 项目结构

    reaper-project-generator/
    ├── app/                 # 源码（collect 收集分组 / durations 时长采样率 / rpp 生成 / gui 界面）
    ├── tests/               # pytest 测试
    ├── CONTRACT.md          # 需求与 .RPP 格式契约（实现依据）
    ├── README.md            # 本文件
    ├── requirements.txt     # 依赖（mutagen）
    ├── start_macos.command  # macOS 启动器
    └── start_windows.bat    # Windows 启动器

## 开发与测试

    cd 本目录
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt pytest
    .venv/bin/python -m pytest tests/ -q

## AI 生成声明

本项目（含全部源码、测试、文档与启动脚本）**完全通过 AI 生成**，生成过程由人类提出需求、验收与反馈，AI 负责设计、编码与测试迭代。
