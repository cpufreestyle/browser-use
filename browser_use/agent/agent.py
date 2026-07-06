"""
Agent 主循环 — 核心文件
========================
一轮决策数据流:
  1. 从浏览器获取页面状态 (DOM 可交互元素列表)
  2. 组装 messages 调用 LLM
  3. 解析 LLM 输出为动作
  4. Controller 执行动作 (Playwright)
  5. 结果加入记忆, 回到第 1 步

Phase 1 改造: 加了大量调试日志 (debug=True 开启)
"""
from __future__ import annotations

import json
import time
import logging
from typing import Any, Optional

from openai import OpenAI

from browser_use.agent.memory import Memory
from browser_use.agent.prompts import get_system_prompt, get_user_prompt
from browser_use.agent.views import (
    AgentHistory, AgentHistoryList, AgentStepInfo, AgentStatus, ActionResult,
)
from browser_use.browser.context import BrowserContext
from browser_use.controller.controller import Controller

logger = logging.getLogger("browser_use.agent")


class Agent:
    """AI 浏览器自动化 Agent"""

    def __init__(
        self,
        task: str,
        llm_client: OpenAI,
        browser_context: Optional[BrowserContext] = None,
        controller: Optional[Controller] = None,
        model: str = "gpt-4o",
        max_steps: int = 50,
        debug: bool = True,
    ):
        self.task = task
        self.llm_client = llm_client
        self.model = model
        self.max_steps = max_steps
        self.debug = debug

        self.browser_context = browser_context or BrowserContext()
        self.controller = controller or Controller()
        self.memory = Memory(get_system_prompt(max_steps), max_steps * 4)
        self.memory.add_user_message(get_user_prompt(task))
        self.status = AgentStatus.IDLE
        self.history = AgentHistoryList()

    async def run(self, max_steps: Optional[int] = None) -> AgentHistoryList:
        """运行 Agent 直到任务完成或达到最大步数"""
        max_steps = max_steps or self.max_steps
        step_info = AgentStepInfo(step_number=1, max_steps=max_steps)
        self.status = AgentStatus.RUNNING
        self._log("=" * 55, level=logging.INFO)
        self._log(f"Agent 启动 | 任务: {self.task}", level=logging.INFO)
        self._log(f"模型: {self.model} | 最大步数: {max_steps}", level=logging.INFO)
        self._log("=" * 55, level=logging.INFO)

        while step_info.step_number <= max_steps:
            if self.status != AgentStatus.RUNNING:
                self._log("Agent 已停止", level=logging.WARNING)
                break
            try:
                done = await self._step(step_info)
                if done:
                    self.status = AgentStatus.DONE
                    self._log("任务完成!", level=logging.INFO)
                    break
                if step_info.is_last_step:
                    self._log("达到最大步数, 强制结束", level=logging.WARNING)
                    self.status = AgentStatus.STOPPED
                    break
            except Exception as e:
                self.status = AgentStatus.ERROR
                self._log(f"步骤 {step_info.step_number} 出错: {e}", level=logging.ERROR)
                logger.exception("Agent step failed")
                break
            step_info.increment()

        self._log_summary()
        return self.history

    async def _step(self, step_info: AgentStepInfo) -> bool:
        """执行一轮决策循环, 返回 True 表示任务完成"""
        step_num = step_info.step_number
        t0 = time.time()

        # 1. 获取页面状态
        self._log(f"--- Step {step_num}: 获取页面状态 ---", level=logging.INFO)
        page_state = await self.browser_context.get_state()
        state_text = page_state.to_text()
        self._log(f"  URL: {page_state.url}", level=logging.DEBUG)
        self._log(f"  标题: {page_state.title}", level=logging.DEBUG)
        self._log(f"  可交互元素: {len(page_state.elements)} 个", level=logging.DEBUG)

        # 2. 调用 LLM
        self._log(f"  调用 LLM...", level=logging.INFO)
        state_msg = self._build_state_message(state_text, step_info)
        self.memory.add_user_message(state_msg)
        self._log(f"  消息数: {len(self.memory)}", level=logging.DEBUG)

        llm_response = self._call_llm()
        self._log(f"  LLM 回复: {llm_response[:200]}", level=logging.DEBUG)
        self.memory.add_assistant_message(llm_response)

        # 3. 解析动作
        action = self._parse_action(llm_response)
        if action is None:
            self._log("  无法解析动作", level=logging.WARNING)
            self.memory.add_action_result("错误: 无法解析回复, 请返回有效 JSON")
            return False

        action_name = action["action"]
        action_params = action.get("params", {})
        self._log(f"  动作: {action_name} | 参数: {action_params}", level=logging.INFO)

        # 4. 执行动作
        result: ActionResult = await self.controller.execute(
            action_name, action_params, self.browser_context
        )
        if result.success:
            self._log(f"  执行成功", level=logging.DEBUG)
            if result.extracted_content:
                self._log(f"  提取: {result.extracted_content[:100]}", level=logging.DEBUG)
        else:
            self._log(f"  执行失败: {result.error_message}", level=logging.WARNING)

        # 5. 记录历史
        duration = time.time() - t0
        self.history.add(AgentHistory(
            step=step_num, url=page_state.url, title=page_state.title,
            state_text=state_text[:200], action_name=action_name,
            action_params=action_params, result=result, duration=duration,
            done=(action_name == "done"),
        ))

        if action_name == "done":
            self._log(f"  完成! 结果: {action_params.get('text', '')}", level=logging.INFO)
            return True

        if result.include_in_memory:
            self.memory.add_action_result(result.extracted_content)
        self.memory.trim()
        self._log(f"  本步耗时: {duration:.2f}s", level=logging.DEBUG)
        return False

    # ---- 辅助方法 ----

    def _build_state_message(self, state_text: str, step_info: AgentStepInfo) -> str:
        remaining = step_info.max_steps - step_info.step_number
        return (
            f"当前页面状态 (剩余 {remaining} 步):\n\n"
            f"{state_text}\n\n"
            f"请选择下一步动作, 返回 JSON。"
        )

    def _call_llm(self) -> str:
        """调用 LLM 并返回文本回复"""
        resp = self.llm_client.chat.completions.create(
            model=self.model,
            messages=self.memory.get_messages(),
            temperature=0.1,
        )
        return resp.choices[0].message.content or ""

    def _parse_action(self, text: str) -> Optional[dict]:
        """从 LLM 回复中解析动作 JSON"""
        try:
            # 尝试提取 JSON（兼容 markdown 代码块）
            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return None

    def _log(self, msg: str, level: int = logging.INFO):
        """调试日志输出"""
        if self.debug or level >= logging.WARNING:
            logger.log(level, msg)

    def _log_summary(self):
        """运行结束的总结日志"""
        self._log("=" * 55, level=logging.INFO)
        self._log(f"运行结束 | 状态: {self.status.value}", level=logging.INFO)
        self._log(f"总步数: {self.history.steps_used} | 总耗时: {self.history.total_duration:.1f}s", level=logging.INFO)
        for h in self.history:
            self._log(f"  {h.summary()}", level=logging.INFO)
        self._log("=" * 55, level=logging.INFO)
