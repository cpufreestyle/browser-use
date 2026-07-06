"""
示例 1: 最简单的用法
====================
让 Agent 完成一个简单任务。
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from browser_use import Agent


async def main():
    # 配置日志 (Phase 1 调试)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # 创建 LLM 客户端 (兼容 StepFun 等第三方 API)
    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    # 创建 Agent
    agent = Agent(
        task="打开 google.com 搜索 'browser-use' 并告诉我第一条结果的标题",
        llm_client=client,
        model=os.getenv("OPENAI_MODEL", "step-1-8k"),
        max_steps=20,
        debug=True,
    )

    # 运行
    history = await agent.run()

    # 打印结果
    print("\n" + "=" * 55)
    print(f"任务结束! 状态: {agent.status.value}")
    print(f"总步数: {history.steps_used} | 总耗时: {history.total_duration:.1f}s")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())
