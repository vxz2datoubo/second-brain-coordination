@echo off
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=utf-8

REM 永久设置用户级环境变量
setx PYTHONIOENCODING "utf-8" >nul 2>&1
setx PYTHONUTF8 "1" >nul 2>&1

REM 永久设置系统级环境变量（需要管理员）
setx /M PYTHONIOENCODING "utf-8" >nul 2>&1
setx /M PYTHONUTF8 "1" >nul 2>&1

REM 强制PowerShell使用UTF-8
setx PSDefaultParameterValues "{'*':Encoding=utf8}" >nul 2>&1

echo [OK] encoding env configured
echo PYTHONIOENCODING=%PYTHONIOENCODING%
echo PYTHONUTF8=%PYTHONUTF8%
echo.
echo NOTE: restart all command windows for full effect
pause
