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
import asyncio
from typing import Any

from playwright.async_api import Page

from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.registry import registry, action

logger = logging.getLogger("browser_use.controller")


class Controller:
    """动作执行引擎 — 根据 action 名查找注册函数并执行"""

    # 动作执行重试配置
    ACTION_MAX_RETRIES = 2
    ACTION_RETRY_DELAY = 0.5  # 重试间隔 0.5s

    async def execute(
        self,
        action_name: str,
        params: dict[str, Any],
        browser_context: BrowserContext,
    ) -> ActionResult:
        """执行一个动作

        改进: 对可重试的动作自动重试, 不让瞬时错误中断 Agent
        """
        if action_name not in registry:
            return ActionResult(
                success=False,
                error_message=f"未知动作: {action_name}. 可用: {registry.list_names()}",
            )

        reg = registry.get(action_name)
        logger.info(f"执行动作: {action_name}({params})")

        last_result = None
        for attempt in range(1, self.ACTION_MAX_RETRIES + 1):
            try:
                result = await reg.func(ctx=browser_context, **params)
                if isinstance(result, ActionResult):
                    if result.success or not self._is_retryable(action_name):
                        return result
                    last_result = result
                    if attempt < self.ACTION_MAX_RETRIES:
                        logger.warning(
                            f"动作 {action_name} 第 {attempt} 次失败: {result.error_message}, "
                            f"{self.ACTION_RETRY_DELAY}s 后重试"
                        )
                        await asyncio.sleep(self.ACTION_RETRY_DELAY)
                    else:
                        logger.error(f"动作 {action_name} 重试 {self.ACTION_MAX_RETRIES} 次后仍失败")
                        return result
                else:
                    return ActionResult(success=True, extracted_content=str(result or ""))
            except Exception as e:
                logger.error(f"动作 {action_name} 执行异常 (第 {attempt} 次): {e}")
                last_result = ActionResult(success=False, error_message=str(e))
                if attempt < self.ACTION_MAX_RETRIES and self._is_retryable(action_name):
                    await asyncio.sleep(self.ACTION_RETRY_DELAY)
                else:
                    return last_result

        return last_result or ActionResult(success=False, error_message="未知错误")

    @staticmethod
    def _is_retryable(action_name: str) -> bool:
        """判断动作是否值得重试"""
        return action_name in ('go_to_url', 'click_element', 'input_text', 'go_back')


# ==========================================
#  内置动作定义
# ==========================================

@action('导航到指定 URL', param_desc={'url': '目标网址'})
async def go_to_url(ctx: BrowserContext, url: str) -> ActionResult:
    """导航到指定 URL — 带内置重试"""
    page = await ctx.get_current_page()
    nav_errors = []
    for attempt in range(1, 3):  # 最多 2 次
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return ActionResult(success=True, extracted_content=f"已导航到 {url}", include_in_memory=True)
        except Exception as e:
            nav_errors.append(str(e))
            if attempt < 2:
                logger.warning(f"导航到 {url} 第 {attempt} 次失败: {e}, 1s 后重试")
                await asyncio.sleep(1)
    return ActionResult(success=False, error_message=f"导航失败 (重试 {len(nav_errors)} 次): {'; '.join(nav_errors)}")


@action('返回上一页')
async def go_back(ctx: BrowserContext) -> ActionResult:
    page = await ctx.get_current_page()
    try:
        await page.go_back(wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        return ActionResult(success=False, error_message=f"返回失败: {e}")
    return ActionResult(success=True, extracted_content="已返回上一页")


@action('点击指定索引的元素', param_desc={'index': '元素索引 (从页面状态获取)'})
async def click_element(ctx: BrowserContext, index: int) -> ActionResult:
    """点击元素 — 带元素等待重试"""
    page = await ctx.get_current_page()
    selector = f'[data-browser-use-index="{index}"]'
    # 等待元素出现, 最多 5s (分两次尝试)
    el = None
    for wait_attempt in range(2):
        try:
            el = await page.wait_for_selector(selector, state='visible', timeout=3000)
            break
        except Exception:
            if wait_attempt == 0:
                # 第一次失败, 尝试滚动到元素位置再试
                await page.evaluate(f"document.querySelector('{selector}')?.scrollIntoView({{block: 'center'}})")
                await asyncio.sleep(0.5)
    if el is None:
        return ActionResult(success=False, error_message=f"找不到或不可见的元素 [{index}]")
    try:
        await el.click(timeout=5000)
    except Exception as e:
        return ActionResult(success=False, error_message=f"点击 [{index}] 失败: {e}")
    try:
        await page.wait_for_load_state('domcontentloaded', timeout=5000)
    except Exception:
        pass  # 页面可能没有导航, 忽略
    return ActionResult(success=True, extracted_content=f"已点击元素 [{index}]", include_in_memory=True)


@action('在指定输入框输入文字', param_desc={'index': '元素索引', 'text': '要输入的文字'})
async def input_text(ctx: BrowserContext, index: int, text: str) -> ActionResult:
    page = await ctx.get_current_page()
    selector = f'[data-browser-use-index="{index}"]'
    try:
        el = await page.wait_for_selector(selector, state='visible', timeout=3000)
    except Exception:
        return ActionResult(success=False, error_message=f"找不到或不可见的输入框 [{index}]")
    try:
        await el.fill(text, timeout=5000)
    except Exception as e:
        return ActionResult(success=False, error_message=f"在 [{index}] 输入失败: {e}")
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
