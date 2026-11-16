@echo off
REM REAPER 工程生成工具 - Windows 启动脚本
setlocal
cd /d "%~dp0"

if not exist .venv (
  echo [rppgen] 创建虚拟环境 .venv ...
  py -3 -m venv .venv 2>nul || python -m venv .venv
)

echo [rppgen] 安装/更新依赖 ...
.venv\Scripts\python -m pip install -q --disable-pip-version-check -r requirements.txt

echo [rppgen] 启动 REAPER 工程生成工具 ...
.venv\Scripts\python -m app
