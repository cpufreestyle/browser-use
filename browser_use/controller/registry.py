"""
动作注册表 — 装饰器模式
========================
这是 browser-use 扩展能力的核心机制。

注册一个自定义动作:
    @action('我的动作', param_desc={'x': '参数说明'})
    async def my_action(ctx, x: int):
        ...

Controller 会自动发现所有用 @action 注册的函数,
LLM 通过系统提示词知道有哪些可用动作。
"""
from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger("browser_use.controller")


@dataclass
class RegisteredAction:
    """一个已注册的动作"""
    name: str
    description: str
    func: Callable[..., Awaitable[Any]]
    param_types: dict[str, str] = field(default_factory=dict)
    param_descs: dict[str, str] = field(default_factory=dict)


class ActionRegistry:
    """动作注册表 — 单例"""

    def __init__(self):
        self._actions: dict[str, RegisteredAction] = {}

    def register(
        self,
        name: str,
        description: str,
        func: Callable,
        param_desc: dict[str, str] | None = None,
    ):
        """注册一个动作"""
        # 提取参数类型
        sig = inspect.signature(func)
        param_types = {}
        param_descs = param_desc or {}
        for pname, param in sig.parameters.items():
            if pname in ("ctx", "context", "self"):
                continue
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                param_types[pname] = "string"
            elif hasattr(annotation, "__name__"):
                param_types[pname] = annotation.__name__
            else:
                param_types[pname] = str(annotation)
            if pname not in param_descs:
                param_descs[pname] = param_types[pname]

        self._actions[name] = RegisteredAction(
            name=name, description=description, func=func,
            param_types=param_types, param_descs=param_descs,
        )
        logger.debug(f"注册动作: {name}")

    def get(self, name: str) -> RegisteredAction | None:
        return self._actions.get(name)

    def list_names(self) -> list[str]:
        return list(self._actions.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._actions

    def __len__(self):
        return len(self._actions)


# 全局单例
registry = ActionRegistry()


def action(description: str, param_desc: dict[str, str] | None = None):
    """
    动作注册装饰器

    用法:
        @action('点击元素', param_desc={'index': '元素索引'})
        async def click_element(ctx, index: int):
            ...
    """
    def decorator(func: Callable):
        registry.register(
            name=func.__name__,
            description=description,
            func=func,
            param_desc=param_desc,
        )
        return func
    return decorator
