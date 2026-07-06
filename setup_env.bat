@echo off
chcp 65001 >nul
echo ========================================
echo   browser-use 环境搭建
echo ========================================

cd /d C:\Users\qm081\browser-use-dev\browser-use

echo [1/4] 创建虚拟环境...
py -m venv .venv

echo [2/4] 激活环境 + 升级 pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [3/4] 安装依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [4/4] 安装 Playwright 浏览器...
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright
playwright install chromium

echo.
echo ========================================
echo   搭建完成!
echo   使用方法:
echo   1. 激活环境: .venv\Scripts\activate
echo   2. 设置 PYTHONPATH: set PYTHONPATH=%CD%
echo   3. 编辑 .env 填入 API Key
echo   4. 测试 DOM: python examples\test_dom.py
echo   5. 运行任务: python run.py "打开百度"
echo ========================================
pause
