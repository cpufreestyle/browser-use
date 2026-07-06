"""
Agent 数据模型
==============
定义 Agent 运行过程中的所有数据结构。
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class AgentStatus(str, Enum):
    """Agent 运行状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    DONE = "done"
    ERROR = "error"


class ActionResult(BaseModel):
    """单个动作的执行结果"""
    success: bool = True
    extracted_content: str = ""
    error_message: str = ""
    include_in_memory: bool = False  # 是否加入对话记忆


class AgentStepInfo(BaseModel):
    """单步执行信息"""
    step_number: int = 1
    max_steps: int = 100

    def increment(self):
        self.step_number += 1

    @property
    def is_last_step(self) -> bool:
        return self.step_number >= self.max_steps - 1


class AgentHistory(BaseModel):
    """一轮交互的完整记录"""
    step: int = 0
    url: str = ""
    title: str = ""
    # LLM 看到的页面状态摘要
    state_text: str = ""
    # LLM 决策的动作（JSON）
    action_name: str = ""
    action_params: dict[str, Any] = Field(default_factory=dict)
    # 动作执行结果
    result: Optional[ActionResult] = None
    # 耗时（秒）
    duration: float = 0.0
    # 是否已完成
    done: bool = False

    def summary(self) -> str:
        """生成简洁摘要（用于调试日志）"""
        status = "✅ DONE" if self.done else f"▶ {self.action_name}"
        return (
            f"[Step {self.step}] {status} | "
            f"URL: {self.url[:60]} | "
            f"耗时: {self.duration:.2f}s"
        )


class AgentHistoryList(BaseModel):
    """完整运行历史"""
    history: list[AgentHistory] = Field(default_factory=list)

    def add(self, entry: AgentHistory):
        self.history.append(entry)

    @property
    def total_duration(self) -> float:
        return sum(h.duration for h in self.history)

    @property
    def steps_used(self) -> int:
        return len(self.history)

    def __len__(self):
        return len(self.history)

    def __iter__(self):
        return iter(self.history)
