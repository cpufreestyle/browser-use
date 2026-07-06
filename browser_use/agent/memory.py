"""
对话记忆管理
============
管理 LLM 的对话历史（messages 列表）。
每轮 Agent 循环会在这里追加：用户状态消息 + AI 决策 + 动作结果。
"""


class Memory:
    """LLM 对话历史管理器"""

    def __init__(self, system_prompt: str, max_messages: int = 200):
        self.messages: list[dict] = []
        self.max_messages = max_messages
        # 初始系统提示
        self.messages.append({"role": "system", "content": system_prompt})

    def add_user_message(self, content: str):
        """添加用户消息（通常是页面状态）"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """添加 AI 回复（动作决策）"""
        self.messages.append({"role": "assistant", "content": content})

    def add_action_result(self, result_text: str):
        """添加动作执行结果（作为用户消息反馈给 LLM）"""
        self.messages.append(
            {"role": "user", "content": f"[动作执行结果]\n{result_text}"}
        )

    def trim(self):
        """裁剪历史，保留系统提示 + 最近的 N 条消息"""
        if len(self.messages) > self.max_messages:
            system = self.messages[0]  # 保留系统提示
            recent = self.messages[-(self.max_messages - 1):]
            self.messages = [system] + recent

    def get_messages(self) -> list[dict]:
        """获取当前消息列表（传给 LLM）"""
        return self.messages

    def __len__(self):
        return len(self.messages)
