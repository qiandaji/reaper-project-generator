#!/bin/bash
# REAPER 工程生成工具 — macOS 启动脚本
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "[rppgen] 创建虚拟环境 .venv ..."
  python3 -m venv .venv
fi

echo "[rppgen] 安装/更新依赖 ..."
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt

echo "[rppgen] 启动 REAPER 工程生成工具 ..."
exec .venv/bin/python -m app
