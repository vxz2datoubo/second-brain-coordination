@echo off
REM 使用 %~dp0 定位脚本所在目录（不再硬编码绝对路径）
cd /d "%~dp0"
REM 优先使用 WORKBUDDY_PYTHON 环境变量；未设置时给出提示
if defined WORKBUDDY_PYTHON (
    "%WORKBUDDY_PYTHON%" bridge.py
) else (
    echo [WARNING] WORKBUDDY_PYTHON 环境变量未设置，尝试使用默认 Python...
    python bridge.py 2>nul || (
        echo [ERROR] 无法找到 Python。请设置 WORKBUDDY_PYTHON 环境变量指向 WorkBuddy Python 解释器。
        echo 示例: set WORKBUDDY_PYTHON=%USERPROFILE%\.workbuddy\binaries\python\envs\chatgpt-bridge\Scripts\python.exe
        pause
        exit /b 1
    )
)
pause
