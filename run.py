"""
browser-use 启动入口
====================
用法:
    python run.py "你的任务描述"
    python run.py --interactive
    python run.py --test-dom
"""
import asyncio
import sys
import logging
import os

# 加载 .env
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from browser_use import Agent
from browser_use.browser.browser import Browser


def setup_logging(debug: bool = True):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_task(task: str, headless: bool = False):
    """运行单个任务"""
    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),   # 兼容 StepFun 等第三方 API
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    browser = Browser(headless=headless)
    ctx = await browser.new_context()

    agent = Agent(
        task=task,
        llm_client=client,
        browser_context=ctx,
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        max_steps=30,
        debug=True,
    )

    try:
        history = await agent.run()
        print(f"\n{'='*55}")
        print(f"任务: {task}")
        print(f"状态: {agent.status.value}")
        print(f"步数: {history.steps_used} | 耗时: {history.total_duration:.1f}s")
        print(f"{'='*55}")
    finally:
        await ctx.close()
        await browser.close()


async def test_dom():
    """测试 DOM 提取 (不消耗 API)"""
    browser = Browser(headless=False)
    ctx = await browser.new_context()
    await ctx.navigate("https://example.com")
    state = await ctx.get_state()
    print(state.to_text())
    await ctx.close()
    await browser.close()


async def interactive():
    """交互模式"""
    print("browser-use 交互模式 (输入 quit 退出)")
    print("=" * 55)
    while True:
        task = input("\n任务> ").strip()
        if task.lower() in ("quit", "exit", "q"):
            break
        if not task:
            continue
        await run_task(task)


def main():
    setup_logging()

    if "--test-dom" in sys.argv:
        asyncio.run(test_dom())
    elif "--interactive" in sys.argv:
        asyncio.run(interactive())
    elif len(sys.argv) > 1:
        task = sys.argv[1]
        asyncio.run(run_task(task))
    else:
        print(__doc__)
        print("\n示例:")
        print('  python run.py "打开百度搜索今天北京天气"')
        print('  python run.py --interactive')
        print('  python run.py --test-dom')


if __name__ == "__main__":
    main()
