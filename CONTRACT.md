# reaper-project-generator — 共享契约（CONTRACT）

本文件由 lead 冻结，是实现方的唯一接口依据。实现方不得修改本文件；若发现契约与 REAPER 实际能力冲突，
先在自己边界内按“回退方案”实现，并在报告中 hand_back 说明冲突点，由 lead 修订。

## 1. 已定决策（访谈收口）
- 形态：独立 Python GUI（tkinter），双击启动，Mac/Win 各配启动器；直接生成 .RPP，无需打开 REAPER。
- 输入：支持多选音频文件；支持选文件夹——每个一级子文件夹各生成一个工程。
- 排列：同一轨道、首尾相接、按文件名自然排序；region 名 = 文件名去扩展名。
- 格式：WAV / AIFF / FLAC / MP3 / M4A / OGG；用 mutagen 读时长。
- 保存：保存对话框，默认预填音频所在目录。

## 2. 目录与职责
reaper-project-generator/
  CONTRACT.md        # lead 所有，实现方只读
  app/               # 实现方所有
    __init__.py
    collect.py       # 收集/分组/自然排序
    durations.py     # mutagen 时长
    rpp.py           # .RPP 构建
    gui.py           # tkinter 界面（薄层，业务逻辑全在 collect/rpp/durations）
    __main__.py      # python -m app 启动 GUI
  tests/             # pytest
  requirements.txt   # mutagen>=1.47
  start_macos.command
  start_windows.bat
  README.md

## 3. 收集与分组规则
- 音频扩展名（大小写不敏感）：.wav .aiff .aif .flac .mp3 .m4a .ogg .oga
- 文件模式：所选文件 = 一个分组，组名 = 文件公共父目录名；无公共目录时组名 "新工程"。
- 文件夹模式：只处理所选文件夹本身 + 其一级子文件夹（不无限递归）：
  - 顶层直接放的音频 → 一个分组，组名 = 所选文件夹名；
  - 每个含音频的一级子文件夹 → 一个分组，组名 = 子文件夹名；
  - 不含音频的子文件夹忽略。
- 每组内按文件名自然排序（不区分大小写，数字按数值：01 < 2 < 10）。
- 文件名含双引号 " 的文件跳过并在日志提示（RPP 字符串无法可靠转义）。

## 4. 时长
- 用 mutagen.File(path).info.length（秒，float）。
- 解析失败的文件跳过并在日志提示；全部分组都为空时报错。

## 5. .RPP 模板（冻结）
UTF-8 编码，LF 行尾。浮点数用 Python repr(float) 最短表示。
GUID = "{" + uuid4().upper() + "}"，每个 ITEM 的 IGUID/TRACK GUID/TRACKID 各自独立生成。

    <REAPER_PROJECT 0.1 "7.0" {int(time.time())}
      RIPPLE 0
      GROUPOVERRIDE 0 0 0
      AUTOXFADE 1
      ENVATTACH 1
      POOLEDENVATTACH 0
      MIXERUIFLAGS 11 48
      PEAKGAIN 1
      FEEDBACK 0
      PANLAW 1
      PROJOFFS 0 0 0
      MAXPROJLEN 0 600
      GRID 3199 8 1 8 1 0 0 0
      TIMEMODE 1 5 -1 30 0 0 -1
      PANMODE 3
      CURSOR 0
      ZOOM 100 0 0
      VZOOMEX 6 0
      USE_REC_CFG 0
      RECMODE 1
      SMPTESYNC 0 30 100 40 1000 300 0 0 1 0 0
      LOOP 0
      LOOPGRAN 0 4
      RECORD_PATH "" ""
      SAMPLERATE {sample_rate} 0 0
      LOCK 0
      GLOBAL_AUTO -1
      TEMPO 120 4 4
      PLAYRATE 1 0 0.25 4
      SELECTION 0 0
      SELECTION2 0 0
      MASTERAUTOMODE 0
      MASTERTRACKHEIGHT 0 0
      MASTERPEAKCOL 16576
      MASTERMUTESOLO 0
      MASTERTRACKVIEW 0 0.6667 0.5 0.5 0 0 0 0 0 0 -1 -1 0 0
      MASTERHWOUT 0 0 1 0 0 0 0 -1
      MASTER_NCH 2 2
      MASTER_VOLUME 1 0 -1 -1 1
      MASTER_FX 1
      MASTER_SEL 0
      MARKER {idx} {start} "{region_name}" 1 0 1 B {GUID} 0
      MARKER {idx} {end} "" 1
      <TRACK {GUID}
        ...track 属性与 ITEM 见下...
      >
    >

- region idx 从 1 起递增；start = 该 item 的 POSITION；end = start + LENGTH；region_name = 文件名去扩展名。
- MARKER 对全部写在 <TRACK 之前（依据 ReaTeam State Chunk Definitions 与 reaproj 实现）。
- sample_rate 默认 44100；GUI 生成时取分组首个音频的实际采样率（读取失败回退 44100）。
- track_name 默认 "PGM"。
- TRACK 属性（来自真实 .RPP fixture，FX 置 0）：
      NAME {track_name}
      PEAKCOL 16576
      BEAT -1
      AUTOMODE 0
      VOLPAN 1 0 -1 -1 1
      MUTESOLO 0 0 0
      IPHASE 0
      PLAYOFFS 0 1
      ISBUS 0 0
      BUSCOMP 0 0 0 0 0
      SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0
      FREEMODE 0
      SEL 0
      REC 0 0 1 0 0 0 0
      VU 2
      TRACKHEIGHT 0 0 0
      INQ 0 0 0 0.5 100 0 0 100
      NCHAN 2
      FX 0
      TRACKID {GUID}
      PERF 0
      MIDIOUT -1
      MAINSEND 1 0
- ITEM 块（每音频一个，POSITION 首尾相接累加，LENGTH = mutagen 时长，IID 从 1 递增）：
        <ITEM
          POSITION {pos}
          SNAPOFFS 0
          LENGTH {length}
          LOOP 1
          ALLTAKES 0
          FADEIN 1 0 0 1 0 0 0
          FADEOUT 1 0 0 1 0 0 0
          MUTE 0 0
          SEL 0
          IGUID {item_guid}
          IID {n}
          NAME {item_name}
          VOLPAN 1 0 1 -1
          SOFFS 0
          PLAYRATE 1 1 0 -1 0 0.0025
          CHANMODE 0
          GUID {take_guid}
          <SOURCE {source_tag}
            FILE "{rel_path}"{mp3_extra}
          >
        >
- item_name = 完整文件名（含扩展名）。
- rel_path = 从 .RPP 所在目录到音频文件的相对路径，统一正斜杠 /。
- source_tag 按音频扩展名（小写）选择：.wav/.aiff/.aif → WAVE；.flac → FLAC；.mp3 → MP3（FILE 行尾追加空格+1，即 mp3_extra）；.m4a/.m4r/.mp4 → VIDEO（SOURCE 行下增加一行 "        FLIP 0 1"）；.ogg/.oga → VORBIS；.opus → OPUS；未知后缀回退 WAVE。
- RPP 字符串：MARKER 名与 FILE 始终双引号包裹；NAME 含空格或非 [A-Za-z0-9._-] 时用双引号包裹。

## 6. GUI 行为（tkinter，中文界面）
- 窗口：顶部“选择文件…”“选择文件夹…”两个按钮；中间列表显示分组（组名 + 文件数）；底部“生成工程”按钮 + 日志文本框。
- 文件模式：askopenfilenames（多选，按 §3 扩展名过滤）。
- 文件夹模式：askdirectory。
- 生成：
  - 单分组 → asksaveasfilename(initialdir=该组音频目录, initialfile="{组名}.rpp", defaultextension=".rpp")。
  - 多分组 → askdirectory(initialdir=所选文件夹) 选保存目录，每个工程自动命名 {组名}.rpp；已存在时逐个 askyesno 确认覆盖，拒绝则跳过该工程。
- 成功后：单工程 → askyesno 是否立即用系统默认方式打开该 .RPP；多工程 → 提示保存目录并打开该目录（mac 用 open，Windows 用 os.startfile）。
- 错误/跳过信息写入日志文本框。

## 7. 启动器
- start_macos.command：cd "$(dirname "$0")"；无 .venv 则 python3 -m venv .venv；
  .venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt；
  exec .venv/bin/python -m app。需 chmod +x。
- start_windows.bat：cd /d "%~dp0"；py -3 -m venv .venv 失败则 python -m venv .venv；
  .venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt；
  .venv\Scripts\python -m app。
- 参考实现：reaper-pgm-control/start_macos.command、reaper-pgm-control/start_windows.bat。

## 8. 测试与验收
- pytest 用例：
  - collect：tmp_path 构造嵌套目录，断言分组、组名、自然排序、非音频忽略、一级子文件夹规则。
  - durations：wave 模块生成 1 秒 WAV，mutagen 读到时长 ≈ 1.0（容差 0.05）。
  - rpp：构造两个假文件（3.5s / 2.25s），断言：头行 <REAPER_PROJECT；两个 MARKER 对（idx 1/2、
    名称=去扩展名、start/end 正确）；恰好一个 <TRACK；两个 <ITEM，POSITION 0 与 3.5，LENGTH 正确；
    SOURCE WAVE FILE 为相对路径；字符串引用符合 §5。
- 全部通过：python -m pytest tests/ -q
- 冒烟：用临时 WAV 实际生成 .RPP 并打印关键行（作为交付证据）。

## 9. 假设清单
- 轨道名默认 "PGM"；.RPP 内用相对路径引用音频；生成成功不自动打开（按 §6 询问）。
- 文件夹模式不无限递归；顶层音频单独成组。
- 无公共目录时组名 "新工程"。
