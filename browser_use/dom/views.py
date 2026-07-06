"""
DOM 数据模型
============
定义从页面提取出的数据结构。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DomElement:
    """页面中一个可交互的元素"""
    index: int            # 给 LLM 用的索引号 [1], [2]...
    tag: str              # HTML 标签 (a, button, input, ...)
    role: str             # 无障碍角色 (button, link, textbox, ...)
    text: str             # 元素文字内容 (截断到 100 字)
    attributes: dict = field(default_factory=dict)  # 关键属性 (href, placeholder, ...)

    def to_line(self) -> str:
        """转成给 LLM 看的一行文本"""
        parts = [f"[{self.index}] <{self.tag}>"]
        if self.role:
            parts.append(f"role={self.role}")
        if self.text:
            parts.append(f'"{self.text[:80]}"')
        for k in ("href", "placeholder", "type", "value"):
            if k in self.attributes and self.attributes[k]:
                parts.append(f"{k}={self.attributes[k][:60]}")
        return " ".join(parts)


@dataclass
class PageState:
    """当前页面完整状态"""
    url: str
    title: str
    elements: list[DomElement] = field(default_factory=list)

    def to_text(self) -> str:
        """转成 LLM 可读的文本"""
        lines = [f"URL: {self.url}", f"标题: {self.title}", "", "可交互元素:"]
        if not self.elements:
            lines.append("  (无)")
        for el in self.elements:
            lines.append(f"  {el.to_line()}")
        return "\n".join(lines)
