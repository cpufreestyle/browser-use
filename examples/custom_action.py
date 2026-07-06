"""
示例 2: 添加自定义动作 (Phase 2)
=================================
演示如何用 @action 装饰器扩展 Agent 的能力。
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from browser_use import Agent, Controller
from browser_use.controller.registry import action
from browser_use.agent.views import ActionResult


# ★ 自定义动作: 截图保存
@action('截图保存到本地', param_desc={'filename': '文件名'})
async def screenshot(ctx, filename: str = "screenshot.png") -> ActionResult:
    page = await ctx.get_current_page()
    import os
    os.makedirs("screenshots", exist_ok=True)
    path = f"screenshots/{filename}"
    await page.screenshot(path=path, full_page=True)
    return ActionResult(
        success=True,
        extracted_content=f"截图已保存: {path}",
        include_in_memory=True,
    )


# ★ 自定义动作: 提取所有链接
@action('提取页面所有链接')
async def extract_links(ctx) -> ActionResult:
    page = await ctx.get_current_page()
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.innerText.trim().substring(0, 50),
            href: a.href
        })).slice(0, 20)
    """)
    import json
    return ActionResult(
        success=True,
        extracted_content=f"页面链接:\n{json.dumps(links, ensure_ascii=False, indent=2)}",
        include_in_memory=True,
    )


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    agent = Agent(
        task="打开 github.com, 截图保存为 github.png, 然后提取页面所有链接",
        llm_client=client,
        model=os.getenv("OPENAI_MODEL", "step-1-8k"),
        max_steps=15,
        debug=True,
    )

    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
