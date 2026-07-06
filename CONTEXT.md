# Context — browser-use 领域语言

> 本文件定义项目的领域语言词汇表。AI 助手在生成 issue、重构提案、假设、测试名等输出时，应使用此处定义的术语，避免同义词漂移。
>
> 当术语或架构决策在实际开发中被确认时，由 `/grill-with-docs` skill 惰性更新本文件。

## 核心概念

| 术语 | 定义 |
|------|------|
| **Agent** | 决策引擎，负责接收任务、调用 LLM、解析动作、执行动作的主循环 |
| **Browser** | Playwright 浏览器进程管理，负责启动/关闭浏览器 |
| **BrowserContext** | 浏览器会话管理，管理页面和状态获取接口 |
| **Controller** | 动作执行引擎，根据动作名在注册表中查找并调用对应函数 |
| **Registry** | 动作注册表，使用 `@action` 装饰器自动注册动作函数 |
| **DomService** | DOM 提取服务，向页面注入 JS 脚本，提取可交互元素 |
| **PageState** | 页面状态数据模型，包含 URL、标题和可交互元素列表 |
| **ActionResult** | 动作执行结果，包含成功/失败状态和提取的内容 |
| **AgentHistory** | Agent 历史记录，记录每一步的 URL、动作、结果、耗时 |
| **Step** | Agent 的一轮决策循环：获取状态 → 调用 LLM → 解析动作 → 执行动作 → 记录历史 |

## 动作（Actions）

Agent 通过执行动作来操作浏览器。内置动作包括：`click_element`、`input_text`、`scroll`、`navigate`、`go_back`、`wait`、`extract_content`、`done` 等。可通过 `@action` 装饰器扩展自定义动作。

## 架构决策记录（ADR）

架构决策记录存放在 `docs/adr/` 目录下，按编号命名（如 `0001-xxx.md`）。

<!-- 当有新的架构决策时，在此处添加链接 -->
