# Phase 3: Web 控制台使用指南

## 架构

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│  React 前端      │ ←─────────────────→ │  FastAPI 后端     │
│  (port 5173)    │     REST API       │  (port 8000)     │
│                 │ ←─────────────────→ │                  │
│  - 任务输入      │                    │  - 创建/停止任务   │
│  - 实时步骤展示  │                    │  - WebSocket推送  │
│  - 日志流        │                    │  - Agent 运行     │
│  - 历史记录      │                    │  - 浏览器管理     │
└─────────────────┘                    └────────┬─────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │  Playwright       │
                                       │  Chromium 浏览器   │
                                       └──────────────────┘
```

## 快速启动

### 方法 1: 一键启动 (推荐)
```
双击 start_console.bat
```

### 方法 2: 手动分步启动

**终端 1 — 后端:**
```bash
cd C:\Users\qm081\browser-use-dev\browser-use
.venv\Scripts\activate
pip install fastapi uvicorn websockets
python -m api.server
```

**终端 2 — 前端:**
```bash
cd C:\Users\qm081\browser-use-dev\browser-use\frontend
npm install
npm run dev
```

### 方法 3: 仅后端 (不用前端)
```bash
python -m api.server
# 然后访问 http://localhost:8000/docs 使用 Swagger UI
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks` | 列出所有任务 |
| GET | `/api/tasks/{id}` | 获取任务详情 |
| POST | `/api/tasks/{id}/stop` | 停止任务 |
| DELETE | `/api/tasks/{id}` | 删除任务 |
| WS | `/ws/tasks/{id}` | WebSocket 实时推送 |

## WebSocket 消息格式

**前端 → 后端:**
```json
{"type": "start"}
```

**后端 → 前端:**
```json
{"type": "step_start", "step": 1, "url": "...", "title": "...", "element_count": 15}
{"type": "action", "step": 1, "action": "click_element", "params": {"index": 3}}
{"type": "step_result", "step": 1, "success": true, "duration": 1.2}
{"type": "done", "status": "done", "total_steps": 5, "total_duration": 12.3}
```

## 前端功能

- **任务输入面板**: 输入任务描述、选模型、设步数、选是否无头
- **实时步骤时间轴**: 每一步的 URL、动作、结果、耗时
- **当前步骤高亮**: 正在执行的步骤实时显示
- **实时日志流**: 每一步的详细日志
- **启动/停止控制**: 一键启动、随时停止
- **运行总结**: 完成后显示总步数和总耗时
