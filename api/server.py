"""
FastAPI 服务器 — Agent Web 控制台后端
=====================================
提供:
  - REST API: 创建任务、查询历史、停止任务
  - WebSocket: 实时推送 Agent 每一步状态

启动:
    python -m api.server
    或
    uvicorn api.server:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件 (OPENAI_API_KEY, OPENAI_BASE_URL 等)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openai import OpenAI

from browser_use import Agent
from browser_use.browser.browser import Browser
from browser_use.agent.views import AgentStatus

logger = logging.getLogger("api")

app = FastAPI(title="Browser-Use 控制台 API", version="0.1.0")

# 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
#  数据模型
# ==========================================

class TaskRequest(BaseModel):
    """创建任务请求"""
    task: str
    model: str = "gpt-4o"
    max_steps: int = 30
    headless: bool = True


class TaskResponse(BaseModel):
    """任务创建响应"""
    task_id: str
    status: str
    created_at: str


class TaskInfo(BaseModel):
    """任务信息"""
    task_id: str
    task: str
    status: str
    steps: list[dict]
    created_at: str
    total_duration: float


# ==========================================
#  全局状态 (简单内存存储, 生产环境换数据库)
# ==========================================

_tasks: dict[str, dict] = {}       # task_id -> task info
_agents: dict[str, Agent] = {}     # task_id -> Agent instance
_browsers: dict[str, Browser] = {} # task_id -> Browser instance


# ==========================================
#  REST API
# ==========================================

@app.get("/api/health")
async def health():
    """健康检查"""
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(req: TaskRequest):
    """创建新任务 (不自动启动, 用 WebSocket 启动)"""
    task_id = str(uuid.uuid4())[:8]
    _tasks[task_id] = {
        "task_id": task_id,
        "task": req.task,
        "status": "idle",
        "steps": [],
        "created_at": datetime.now().isoformat(),
        "total_duration": 0.0,
        "model": req.model,
        "max_steps": req.max_steps,
        "headless": req.headless,
    }
    return TaskResponse(
        task_id=task_id, status="idle",
        created_at=_tasks[task_id]["created_at"],
    )


@app.get("/api/tasks", response_model=list[TaskInfo])
async def list_tasks():
    """列出所有任务"""
    return [TaskInfo(**t) for t in _tasks.values()]


@app.get("/api/tasks/{task_id}", response_model=TaskInfo)
async def get_task(task_id: str):
    """获取单个任务详情"""
    if task_id not in _tasks:
        return {"error": "Task not found"}
    return TaskInfo(**_tasks[task_id])


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    """停止任务"""
    if task_id in _agents:
        agent = _agents[task_id]
        agent.status = AgentStatus.STOPPED
        _tasks[task_id]["status"] = "stopped"
    return {"status": "stopped"}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务"""
    if task_id in _agents:
        agent = _agents[task_id]
        agent.status = AgentStatus.STOPPED
    if task_id in _browsers:
        browser = _browsers[task_id]
        await browser.close()
    _tasks.pop(task_id, None)
    _agents.pop(task_id, None)
    _browsers.pop(task_id, None)
    return {"status": "deleted"}


# ==========================================
#  WebSocket — 实时推送 Agent 状态
# ==========================================

@app.websocket("/ws/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    """
    WebSocket 连接 — 实时推送 Agent 每一步状态

    前端连接后发送 {"type": "start"} 启动任务,
    后端每一步推送:
      {"type": "step", "step": 1, "url": "...", "action": "...", ...}
      {"type": "done", "result": "..."}
      {"type": "error", "message": "..."}
    """
    await websocket.accept()

    if task_id not in _tasks:
        await websocket.send_json({"type": "error", "message": "Task not found"})
        await websocket.close()
        return

    task_info = _tasks[task_id]
    task_info["status"] = "running"

    # 等待前端发送 start 信号
    try:
        msg = await websocket.receive_text()
        data = json.loads(msg)
        if data.get("type") != "start":
            await websocket.send_json({"type": "error", "message": "Send {type: start} first"})
            await websocket.close()
            return
    except (WebSocketDisconnect, json.JSONDecodeError):
        await websocket.close()
        return

    # 创建并运行 Agent
    try:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("sk-your"):
            await websocket.send_json({
                "type": "error",
                "message": "OPENAI_API_KEY 未配置! 请编辑 .env 文件, 填入真实的 API Key。",
            })
            await websocket.close()
            return

        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),   # 兼容 StepFun 等第三方 API
            api_key=api_key,
        )
        # 模型: 优先用请求中指定的, 否则回退到 .env 里的 OPENAI_MODEL
        model = task_info.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o")
        browser = Browser(headless=task_info.get("headless", True))
        _browsers[task_id] = browser
        ctx = await browser.new_context()

        agent = Agent(
            task=task_info["task"],
            llm_client=client,
            browser_context=ctx,
            model=model,
            max_steps=task_info.get("max_steps", 30),
            debug=False,  # 日志走 WebSocket, 不走 console
        )
        _agents[task_id] = agent

        # 发送任务开始
        await websocket.send_json({
            "type": "start",
            "task": task_info["task"],
            "model": model,
            "max_steps": agent.max_steps,
        })

        # 运行 Agent, 每一步推送状态
        await _run_agent_with_streaming(agent, task_id, websocket)

    except Exception as e:
        error_msg = str(e).strip()
        if not error_msg:
            error_msg = f"{type(e).__name__}: {repr(e)}"
        logger.exception("Agent run failed")
        await websocket.send_json({"type": "error", "message": error_msg})
    finally:
        task_info["status"] = "done"
        await ctx.close()
        await browser.close()
        _browsers.pop(task_id, None)
        await websocket.close()


async def _run_agent_with_streaming(agent: Agent, task_id: str, ws: WebSocket):
    """运行 Agent 并通过 WebSocket 推送每一步状态"""

    from browser_use.agent.views import AgentStepInfo
    step_info = AgentStepInfo(step_number=1, max_steps=agent.max_steps)
    agent.status = AgentStatus.RUNNING

    while step_info.step_number <= agent.max_steps:
        if agent.status != AgentStatus.RUNNING:
            await ws.send_json({"type": "stopped", "step": step_info.step_number})
            break

        try:
            done = await _streaming_step(agent, step_info, task_id, ws)
            if done:
                break
            if step_info.is_last_step:
                await ws.send_json({"type": "max_steps_reached"})
                break
        except Exception as e:
            await ws.send_json({"type": "error", "message": str(e)})
            break

        step_info.increment()

    # 发送最终总结
    await ws.send_json({
        "type": "done",
        "status": agent.status.value,
        "total_steps": agent.history.steps_used,
        "total_duration": round(agent.history.total_duration, 2),
        "history": [
            {
                "step": h.step, "url": h.url, "title": h.title,
                "action": h.action_name, "params": h.action_params,
                "success": h.result.success if h.result else False,
                "duration": round(h.duration, 2),
            }
            for h in agent.history
        ],
    })


async def _streaming_step(agent: Agent, step_info, task_id: str, ws: WebSocket):
    """单步执行 + WebSocket 推送"""
    import time
    step_num = step_info.step_number
    t0 = time.time()

    # 1. 获取页面状态
    page_state = await agent.browser_context.get_state()
    await ws.send_json({
        "type": "step_start",
        "step": step_num,
        "url": page_state.url,
        "title": page_state.title,
        "element_count": len(page_state.elements),
    })

    # 2. 调用 LLM
    state_msg = agent._build_state_message(page_state.to_text(), step_info)
    agent.memory.add_user_message(state_msg)
    llm_response = agent._call_llm()
    agent.memory.add_assistant_message(llm_response)

    # 3. 解析动作
    action = agent._parse_action(llm_response)
    if action is None:
        await ws.send_json({"type": "warning", "message": "无法解析动作"})
        agent.memory.add_action_result("错误: 无法解析回复")
        return False

    action_name = action["action"]
    action_params = action.get("params", {})

    await ws.send_json({
        "type": "action",
        "step": step_num,
        "action": action_name,
        "params": action_params,
        "llm_response": llm_response[:500],
    })

    # 4. 执行
    from browser_use.agent.views import ActionResult, AgentHistory
    result = await agent.controller.execute(
        action_name, action_params, agent.browser_context
    )

    duration = time.time() - t0
    agent.history.add(AgentHistory(
        step=step_num, url=page_state.url, title=page_state.title,
        state_text=page_state.to_text()[:200],
        action_name=action_name, action_params=action_params,
        result=result, duration=duration, done=(action_name == "done"),
    ))

    # 推送执行结果
    await ws.send_json({
        "type": "step_result",
        "step": step_num,
        "success": result.success,
        "extracted_content": result.extracted_content[:500] if result.extracted_content else "",
        "error": result.error_message,
        "duration": round(duration, 2),
    })

    # 更新任务存储
    _tasks[task_id]["steps"].append({
        "step": step_num, "url": page_state.url, "title": page_state.title,
        "action": action_name, "params": action_params,
        "success": result.success, "duration": round(duration, 2),
    })
    _tasks[task_id]["total_duration"] += duration

    if action_name == "done":
        return True

    if result.include_in_memory:
        agent.memory.add_action_result(result.extracted_content)
    agent.memory.trim()
    return False


# ==========================================
#  启动入口
# ==========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)
