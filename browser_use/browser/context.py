"""
BrowserContext — 浏览器会话管理
================================
管理当前页面、标签页、页面状态提取。
Agent 每一步都通过它拿到页面状态。
"""
from __future__ import annotations

import logging
from typing import Optional

from playwright.async_api import BrowserContext as PwContext, Page

from browser_use.dom.service import DomService
from browser_use.dom.views import PageState

logger = logging.getLogger("browser_use.browser")


class BrowserContext:
    """浏览器上下文 — 管理页面和状态提取"""

    def __init__(self, pw_context: Optional[PwContext] = None):
        self.pw_context = pw_context
        self._page: Optional[Page] = None
        self._dom_service = DomService()

    async def _ensure_context(self):
        """如果没有上下文, 自动创建 Browser + Context"""
        if self.pw_context is None:
            from browser_use.browser.browser import Browser
            browser = Browser(headless=True)
            ctx = await browser.new_context()
            self.pw_context = ctx.pw_context

    async def get_current_page(self) -> Page:
        """获取当前活动页面"""
        await self._ensure_context()
        if self._page is None or self._page.is_closed():
            self._page = await self.pw_context.new_page()
            logger.info("新建页面")
        return self._page

    async def get_state(self) -> PageState:
        """提取当前页面状态 (URL, 标题, 可交互元素列表)"""
        page = await self.get_current_page()
        return await self._dom_service.get_page_state(page)

    async def navigate(self, url: str):
        """导航到指定 URL"""
        page = await self.get_current_page()
        logger.info(f"导航到: {url}")
        await page.goto(url, wait_until="domcontentloaded")

    async def close(self):
        """关闭上下文"""
        if self._page and not self._page.is_closed():
            await self._page.close()
        if self.pw_context:
            await self.pw_context.close()
