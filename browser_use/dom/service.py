"""
DomService — 页面状态提取服务
==============================
注入 JS 脚本到页面，遍历 DOM 树，找出所有可交互元素，
给每个元素打上 data-browser-use-index 属性，返回结构化的 PageState。

这是 Agent "看到" 页面的方式 —— 不是截图，而是结构化的元素列表。
"""
from __future__ import annotations

import logging
from playwright.async_api import Page

from browser_use.dom.views import PageState, DomElement

logger = logging.getLogger("browser_use.dom")

# 注入到页面的 JS 脚本：提取可交互元素
_EXTRACT_JS = """
() => {
    const interactiveSelectors = [
        'a', 'button', 'input', 'select', 'textarea',
        '[role="button"]', '[role="link"]', '[role="tab"]',
        '[role="menuitem"]', '[role="checkbox"]', '[role="radio"]',
        '[onclick]', '[contenteditable="true"]'
    ];
    const seen = new Set();
    const results = [];
    let index = 1;

    for (const selector of interactiveSelectors) {
        for (const el of document.querySelectorAll(selector)) {
            if (seen.has(el)) continue;
            if (el.offsetParent === null && el.tagName !== 'INPUT') continue;
            seen.add(el);

            // 打上索引标记
            el.setAttribute('data-browser-use-index', String(index));

            const tag = el.tagName.toLowerCase();
            const role = el.getAttribute('role') || '';
            const text = (el.innerText || el.textContent || '').trim();
            const attrs = {};
            for (const k of ['href', 'placeholder', 'type', 'value', 'name', 'aria-label']) {
                const v = el.getAttribute(k);
                if (v) attrs[k] = v;
            }

            results.push({index, tag, role, text: text.substring(0, 100), attributes: attrs});
            index++;
        }
    }
    return results;
}
"""


class DomService:
    """页面 DOM 提取服务"""

    async def get_page_state(self, page: Page) -> PageState:
        """提取当前页面的完整状态"""
        url = page.url
        title = await page.title()

        # 注入 JS 提取可交互元素
        try:
            raw_elements = await page.evaluate(_EXTRACT_JS)
        except Exception as e:
            logger.warning(f"DOM 提取失败: {e}")
            raw_elements = []

        elements = [
            DomElement(
                index=e["index"],
                tag=e["tag"],
                role=e["role"],
                text=e["text"],
                attributes=e.get("attributes", {}),
            )
            for e in raw_elements
        ]

        logger.debug(f"提取到 {len(elements)} 个可交互元素 from {url}")
        return PageState(url=url, title=title, elements=elements)
