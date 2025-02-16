@echo off
setlocal EnableDelayedExpansion

echo [92m正在激活虚拟环境...[0m

cd /d "%~dp0"

call .\venv\Scripts\activate.bat
if errorlevel 1 (
    echo [91m激活虚拟环境失败[0m
    exit /b 1
)

echo [92m虚拟环境已激活[0m
echo [92m正在启动项目...[0m

python main.py
if errorlevel 1 (
    echo [91m启动项目失败[0m
    exit /b 1
)