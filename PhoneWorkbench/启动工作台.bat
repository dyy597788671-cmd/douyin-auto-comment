@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 run.py
  pause
  exit /b
)
where python >nul 2>nul
if not errorlevel 1 (
  python run.py
  pause
  exit /b
)
echo 未检测到 Python。请将 docs\交给本地AI.md 发给本地 AI 完成环境检查。
pause
