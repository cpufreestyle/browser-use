"""
browser-use 核心包
=================
AI 浏览器自动化 Agent —— 让 LLM 像人一样操作浏览器。

核心架构：
    用户任务 → Agent 循环 → [DOM提取 → LLM决策 → 动作执行] → 完成

模块说明：
    agent/      — Agent 主循环、记忆管理、系统提示词
    browser/    — Playwright 浏览器管理（启动/关闭/多标签页）
    controller/ — 动作注册与执行（click, input, scroll, ...）
    dom/        — DOM 树提取，把页面变成 LLM 能读的结构化文本
"""

from browser_use.agent.agent import Agent
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.controller.controller import Controller
from browser_use.controller.registry import registry

__version__ = "0.1.0-dev"
__all__ = [
    "Agent",
    "Browser",
    "BrowserContext",
    "Controller",
    "registry",
]
