"""
Controller — 动作执行引擎
=========================
负责执行 LLM 决策出来的动作。

内置动作: go_to_url, go_back, click_element, input_text,
         scroll_down, scroll_up, send_keys, extract_content, done

★ Phase 2 扩展点: 用 @action 装饰器在文件底部添加自定义动作
"""
from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page

from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.registry import registry, action

logger = logging.getLogger("browser_use.controller")


class Controller:
    """动作执行引擎 — 根据 action 名查找注册函数并执行"""

    async def execute(
        self,
        action_name: str,
        params: dict[str, Any],
        browser_context: BrowserContext,
    ) -> ActionResult:
        """执行一个动作"""
        if action_name not in registry:
            return ActionResult(
                success=False,
                error_message=f"未知动作: {action_name}. 可用: {registry.list_names()}",
            )

        reg = registry.get(action_name)
        logger.info(f"执行动作: {action_name}({params})")

        try:
            # 把 browser_context 作为 ctx 传入
            result = await reg.func(ctx=browser_context, **params)
            if isinstance(result, ActionResult):
                return result
            return ActionResult(success=True, extracted_content=str(result or ""))
        except Exception as e:
            logger.error(f"动作 {action_name} 执行失败: {e}")
            return ActionResult(success=False, error_message=str(e))


# ==========================================
#  内置动作定义
# ==========================================

@action('导航到指定 URL', param_desc={'url': '目标网址'})
async def go_to_url(ctx: BrowserContext, url: str) -> ActionResult:
    page = await ctx.get_current_page()
    await page.goto(url, wait_until="domcontentloaded")
    return ActionResult(success=True, extracted_content=f"已导航到 {url}", include_in_memory=True)


@action('返回上一页')
async def go_back(ctx: BrowserContext) -> ActionResult:
    page = await ctx.get_current_page()
    await page.go_back(wait_until="domcontentloaded")
    return ActionResult(success=True, extracted_content="已返回上一页")


@action('点击指定索引的元素', param_desc={'index': '元素索引 (从页面状态获取)'})
async def click_element(ctx: BrowserContext, index: int) -> ActionResult:
    page = await ctx.get_current_page()
    # 通过 data-browser-use-index 属性定位元素
    selector = f'[data-browser-use-index="{index}"]'
    el = await page.query_selector(selector)
    if el is None:
        return ActionResult(success=False, error_message=f"找不到索引为 {index} 的元素")
    await el.click(timeout=5000)
    await page.wait_for_load_state("domcontentloaded", timeout=10000)
    return ActionResult(success=True, extracted_content=f"已点击元素 [{index}]", include_in_memory=True)


@action('在指定输入框输入文字', param_desc={'index': '元素索引', 'text': '要输入的文字'})
async def input_text(ctx: BrowserContext, index: int, text: str) -> ActionResult:
    page = await ctx.get_current_page()
    selector = f'[data-browser-use-index="{index}"]'
    el = await page.query_selector(selector)
    if el is None:
        return ActionResult(success=False, error_message=f"找不到索引为 {index} 的输入框")
    await el.fill(text)
    return ActionResult(success=True, extracted_content=f"已在 [{index}] 输入: {text}", include_in_memory=True)


@action('向下滚动页面', param_desc={'amount': '滚动幅度 (默认3)'})
async def scroll_down(ctx: BrowserContext, amount: int = 3) -> ActionResult:
    page = await ctx.get_current_page()
    await page.evaluate(f"window.scrollBy(0, {amount} * 300)")
    return ActionResult(success=True, extracted_content=f"向下滚动 {amount} 格")


@action('向上滚动页面', param_desc={'amount': '滚动幅度 (默认3)'})
async def scroll_up(ctx: BrowserContext, amount: int = 3) -> ActionResult:
    page = await ctx.get_current_page()
    await page.evaluate(f"window.scrollBy(0, -{amount} * 300)")
    return ActionResult(success=True, extracted_content=f"向上滚动 {amount} 格")


@action('发送键盘按键', param_desc={'keys': '按键名 如 Enter, Escape'})
async def send_keys(ctx: BrowserContext, keys: str) -> ActionResult:
    page = await ctx.get_current_page()
    await page.keyboard.press(keys)
    return ActionResult(success=True, extracted_content=f"已按键: {keys}")


@action('从当前页面提取内容', param_desc={'goal': '要提取什么内容'})
async def extract_content(ctx: BrowserContext, goal: str) -> ActionResult:
    page = await ctx.get_current_page()
    title = await page.title()
    url = page.url
    # 简单提取页面文本 (实际版本会用 LLM 做结构化提取)
    text = await page.evaluate("document.body.innerText.substring(0, 3000)")
    return ActionResult(
        success=True,
        extracted_content=f"[{title}] ({url})\n提取目标: {goal}\n页面内容:\n{text}",
        include_in_memory=True,
    )


@action('任务完成', param_desc={'text': '最终结果说明'})
async def done(ctx: BrowserContext, text: str = "") -> ActionResult:
    return ActionResult(success=True, extracted_content=text, include_in_memory=True)


# ==========================================
#  ★ Phase 2 扩展示例 — 取消注释即可使用
# ==========================================

# @action('截图保存到本地', param_desc={'filename': '文件名'})
# async def screenshot(ctx: BrowserContext, filename: str = "screenshot.png") -> ActionResult:
#     page = await ctx.get_current_page()
#     path = f"screenshots/{filename}"
#     import os; os.makedirs("screenshots", exist_ok=True)
#     await page.screenshot(path=path, full_page=True)
#     return ActionResult(success=True, extracted_content=f"截图已保存: {path}")
