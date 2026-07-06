@echo off
chcp 65001 >nul
echo ========================================
echo   Browser-Use 控制台 一键启动
echo ========================================
echo.

cd /d C:\Users\qm081\browser-use-dev\browser-use

REM 设置 PYTHONPATH 使 browser_use 包可被导入
set PYTHONPATH=%CD%

REM Node.js PATH (如果 npm 不在系统 PATH 中)
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "D:\Program Files\nodejs\npm.cmd" (
        set PATH=D:\Program Files\nodejs;%PATH%
    )
)

REM Node.js 内存限制 (避免 Vite OOM)
set NODE_OPTIONS=--max-old-space-size=4096

echo [1/2] 启动后端 (FastAPI, 端口 8000)...
start "Browser-Use API" cmd /k "cd /d C:\Users\qm081\browser-use-dev\browser-use && set PYTHONPATH=%CD% && call .venv\Scripts\activate.bat && python -m api.server"

timeout /t 3 /nobreak >nul

echo [2/2] 启动前端 (Vite, 端口 5173)...
cd frontend
if not exist node_modules (
    echo 安装前端依赖...
    call npm install
)
start "Browser-Use Frontend" cmd /k "cd C:\Users\qm081\browser-use-dev\browser-use\frontend && set NODE_OPTIONS=--max-old-space-size=4096 && npm run dev"

echo.
echo ========================================
echo   启动完成!
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo ========================================
echo.
echo 关闭窗口即可停止服务
pause
