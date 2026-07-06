"""
Browser — Playwright 浏览器实例管理
====================================
负责浏览器的启动和关闭。
BrowserContext 是它的"会话层"，管理页面状态。
"""
from __future__ import annotations

import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser as PwBrowser, Playwright

logger = logging.getLogger("browser_use.browser")


class Browser:
    """Playwright 浏览器管理器"""

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        slow_mo: int = 0,
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.slow_mo = slow_mo
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[PwBrowser] = None

    async def start(self) -> PwBrowser:
        """启动浏览器"""
        if self._browser is not None:
            return self._browser
        logger.info(f"启动 {self.browser_type} (headless={self.headless})")
        self._playwright = await async_playwright().start()
        browser_method = getattr(self._playwright, self.browser_type)
        self._browser = await browser_method.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        logger.info("浏览器已启动")
        return self._browser

    async def new_context(self) -> "BrowserContext":
        """创建新的浏览器上下文"""
        from browser_use.browser.context import BrowserContext
        browser = await self.start()
        pw_context = await browser.new_context(
            viewport={"width": 1280, "height": 1024},
            locale="zh-CN",
        )
        return BrowserContext(pw_context=pw_context)

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        logger.info("浏览器已关闭")
