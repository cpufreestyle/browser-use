# browser-use 架构说明

> 本文档帮助你理解项目的核心设计，是你"学源码"的第一份地图。

## 一、项目结构

```
browser-use/
├── browser_use/                 # 核心包
│   ├── __init__.py              # 包入口, 导出主要类
│   ├── agent/                   # ★ Agent 决策引擎
│   │   ├── __init__.py
│   │   ├── agent.py             # ★★★ 主循环 — 整个项目的心脏
│   │   ├── memory.py            # LLM 对话历史管理
│   │   ├── prompts.py           # 系统提示词 (改这里改变 Agent 行为)
│   │   └── views.py             # 数据模型 (AgentHistory, ActionResult, ...)
│   ├── browser/                 # 浏览器管理
│   │   ├── __init__.py
│   │   ├── browser.py           # Playwright 浏览器启动/关闭
│   │   └── context.py           # 浏览器会话 (页面管理 + 状态获取)
│   ├── controller/              # ★ 动作执行引擎
│   │   ├── __init__.py
│   │   ├── registry.py          # ★ 动作注册表 (装饰器模式)
│   │   └── controller.py        # 动作执行 + 内置动作定义
│   └── dom/                     # DOM 提取
│       ├── __init__.py
│       ├── service.py           # 注入 JS, 提取可交互元素
│       └── views.py             # DomElement, PageState 数据模型
├── examples/                    # 示例代码
│   ├── simple.py                # 最简用法
│   ├── custom_action.py         # Phase 2: 自定义动作示例
│   └── test_dom.py              # 不用 LLM, 测试 DOM 提取
├── run.py                       # 启动入口
├── requirements.txt             # Python 依赖
├── setup_env.bat                # 一键环境搭建 (Windows)
├── .env.example                 # 环境变量模板
└── ARCHITECTURE.md              # 本文档
```

## 二、核心数据流（必读）

Agent 每一步的数据流:

```
                    ┌─────────────────────────────────────────┐
                    │              Agent._step()               │
                    │              (agent.py)                   │
                    └─────────────────────────────────────────┘
                                     │
         ┌───────────────┬───────────┼───────────┬─────────────┐
         ▼               ▼           ▼           ▼             ▼
    ① 获取页面状态   ② 调用 LLM   ③ 解析动作  ④ 执行动作   ⑤ 记录历史
    (context.py)    (memory +    (JSON 解析)  (controller)  (history)
                     OpenAI)
         │               │                       │
         ▼               ▼                       ▼
    DomService       messages[]            Playwright
    注入 JS          → LLM API             操作浏览器
    提取元素         ← 动作 JSON            click/input/...
         │                                       │
         ▼                                       ▼
    PageState                              ActionResult
    .to_text()                             .extracted_content
    → 喂给 LLM                             → 加入记忆
```

### 详细步骤说明:

**① 获取页面状态** (`DomService.get_page_state`)
- 向页面注入 JavaScript 脚本
- 遍历 DOM, 找出所有可交互元素 (a, button, input, ...)
- 给每个元素打上 `data-browser-use-index` 属性
- 返回 `PageState` (url + title + elements 列表)

**② 调用 LLM** (`Agent._call_llm`)
- 把页面状态文本 + 对话历史 组装成 messages
- 调用 OpenAI API
- LLM 返回动作 JSON, 如 `{"action": "click_element", "params": {"index": 3}}`

**③ 解析动作** (`Agent._parse_action`)
- 从 LLM 回复中提取 JSON
- 返回 `{"action": "动作名", "params": {...}}`

**④ 执行动作** (`Controller.execute`)
- 根据动作名在 `registry` 中查找注册函数
- 调用该函数, 通过 Playwright 操作浏览器
- 返回 `ActionResult`

**⑤ 记录历史** (`AgentHistoryList`)
- 记录这一步的全部信息 (url, 动作, 结果, 耗时)
- 把结果反馈到 LLM 记忆中
- 回到 ① 继续下一步

## 三、模块详解

### agent/ — 决策引擎

| 文件 | 作用 | 学习要点 |
|------|------|---------|
| `agent.py` | 主循环 `run()` → `_step()` | Agent 状态机怎么转 |
| `memory.py` | 对话历史 messages 列表 | 怎么管理 LLM 上下文窗口 |
| `prompts.py` | 系统提示词 | 改这里就能改变 Agent 行为 |
| `views.py` | 数据模型 | ActionResult / AgentHistory 的字段 |

**核心函数调用链**:
```
Agent.run()
  └→ Agent._step()           ← 一轮决策
       ├→ BrowserContext.get_state()
       │    └→ DomService.get_page_state()
       │         └→ page.evaluate(JS)  ← 注入脚本提取 DOM
       ├→ Agent._build_state_message()
       ├→ Agent._call_llm()   ← 调 OpenAI API
       ├→ Agent._parse_action()
       └→ Controller.execute()
            └→ registry.get(action_name).func()
                 └→ Playwright 操作浏览器
```

### browser/ — 浏览器管理

| 文件 | 作用 |
|------|------|
| `browser.py` | Browser 类: 启动/关闭 Playwright 浏览器 |
| `context.py` | BrowserContext: 管理页面, 提供状态获取接口 |

两层分离的设计: Browser 管"进程", Context 管"会话"。
一个 Browser 可以有多个 Context (多标签页/隔离会话)。

### controller/ — 动作执行

| 文件 | 作用 |
|------|------|
| `registry.py` | `@action` 装饰器 + 全局注册表 |
| `controller.py` | 执行引擎 + 9 个内置动作 |

**★ 这是 Phase 2 的核心扩展点**。加新动作只需:
```python
@action('描述', param_desc={'param': '说明'})
async def my_action(ctx, param: str) -> ActionResult:
    page = await ctx.get_current_page()
    ...
    return ActionResult(success=True, extracted_content="结果")
```
注册表自动发现, 系统提示词里自动列出。

### dom/ — DOM 提取

| 文件 | 作用 |
|------|------|
| `service.py` | 注入 JS 脚本, 返回 PageState |
| `views.py` | DomElement / PageState 数据模型 |

Agent "看" 页面的方式不是截图, 而是结构化的元素列表:
```
[1] <a> role=link "GitHub" href=https://github.com
[2] <input> role=textbox placeholder="搜索" type=text
[3] <button> role=button "登录"
```

## 四、Phase 1 改造说明（已内置）

`agent.py` 中已加入大量调试日志, 通过 `debug=True` 开启:

| 日志位置 | 内容 | 级别 |
|---------|------|------|
| Agent 启动 | 任务、模型、最大步数 | INFO |
| 每步开始 | URL、标题、元素数量 | DEBUG |
| LLM 调用 | 消息数、LLM 回复前 200 字 | DEBUG |
| 动作解析 | 动作名、参数 | INFO |
| 动作执行 | 成功/失败、提取内容 | DEBUG |
| 单步结束 | 耗时 | DEBUG |
| 运行结束 | 总步数、总耗时、每步摘要 | INFO |

运行 `python run.py --test-dom` 可查看页面状态提取效果 (不消耗 API)。

## 五、后续改造路线

| Phase | 内容 | 改哪里 |
|-------|------|--------|
| Phase 1 ✅ | 调试日志 | `agent.py` (已完成) |
| Phase 2 | 自定义动作 | `controller/controller.py` 底部加 `@action` |
| Phase 3 | Web 控制台 | 新建 `api/` + `frontend/` 目录 |
| Phase 4 | 多 Agent / 录制回放 | 扩展 `agent/` 模块 |
