@echo off
chcp 65001 >nul
echo ════════════════════════════════════════
echo   Browser-Use 全栈环境一键搭建
echo   后端 Python + 前端 React
echo ════════════════════════════════════════
echo.

cd /d C:\Users\qm081\browser-use-dev\browser-use

echo [1/5] 创建 Python 虚拟环境...
if not exist .venv (
    py -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/5] 升级 pip + 安装后端依赖...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [3/5] 安装 Playwright Chromium...
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
playwright install chromium

echo [4/5] 安装前端依赖...
cd frontend
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "D:\Program Files\nodejs\npm.cmd" (
        set PATH=D:\Program Files\nodejs;%PATH%
    )
)
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   ⚠️ 未找到 npm, 请先安装 Node.js: https://nodejs.org
    echo   跳过前端安装, 后端仍可使用
) else (
    if not exist node_modules (
        npm install
    )
)
cd ..

echo [5/5] 检查 .env 文件...
if not exist .env (
    copy .env.example .env
    echo   已创建 .env, 请编辑填入 OPENAI_API_KEY
)

echo.
echo ════════════════════════════════════════
echo   搭建完成!
echo ════════════════════════════════════════
echo.
echo   下一步:
echo   1. 编辑 .env 填入 OPENAI_API_KEY
echo   2. 设置 PYTHONPATH: set PYTHONPATH=%CD%
echo   3. 测试 DOM 提取 (不耗 API):
echo      python examples\test_dom.py
echo   4. 启动 Web 控制台:
echo      双击 start_console.bat
echo   5. 或命令行运行:
echo      python run.py "打开百度搜索今天北京天气"
echo.
pause
