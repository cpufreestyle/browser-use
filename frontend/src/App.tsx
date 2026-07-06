import { useState, useRef, useCallback, useEffect } from 'react'
import type { WsMessage, StepRecord, RunStatus } from './types'

// ==========================================
//  主组件
// ==========================================

export default function App() {
  const [task, setTask] = useState('打开 google.com 搜索 "browser-use" 并返回第一条结果的标题')
  const [model, setModel] = useState('step-1-8k')
  const [maxSteps, setMaxSteps] = useState(30)
  const [headless, setHeadless] = useState(false)
  const [status, setStatus] = useState<RunStatus>('idle')
  const [steps, setSteps] = useState<StepRecord[]>([])
  const [liveStep, setLiveStep] = useState<WsMessage | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [taskId, setTaskId] = useState<string>('')
  const [summary, setSummary] = useState<{ total: number; duration: number } | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const logEndRef = useRef<HTMLDivElement>(null)

  const addLog = useCallback((msg: string) => {
    const ts = new Date().toLocaleTimeString('zh-CN')
    setLogs(prev => [...prev, `[${ts}] ${msg}`])
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // 创建任务并连接 WebSocket
  const startTask = async () => {
    setSteps([])
    setLogs([])
    setLiveStep(null)
    setSummary(null)
    setStatus('connecting')

    try {
      // 1. 创建任务
      const resp = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, model, max_steps: maxSteps, headless }),
      })
      const data = await resp.json()
      setTaskId(data.task_id)
      addLog(`任务已创建: ${data.task_id}`)

      // 2. 连接 WebSocket
      const wsProtocol = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${wsProtocol}://${location.host}/ws/tasks/${data.task_id}`)
      wsRef.current = ws

      ws.onopen = () => {
        addLog('WebSocket 已连接, 发送启动信号...')
        ws.send(JSON.stringify({ type: 'start' }))
        setStatus('running')
      }

      ws.onmessage = (ev) => {
        const msg: WsMessage = JSON.parse(ev.data)
        handleMessage(msg)
      }

      ws.onerror = () => {
        addLog('WebSocket 连接出错')
        setStatus('error')
      }

      ws.onclose = () => {
        addLog('WebSocket 已关闭')
        if (status === 'running') setStatus('done')
      }
    } catch (e) {
      addLog(`创建任务失败: ${e}`)
      setStatus('error')
    }
  }

  // 处理 WebSocket 消息
  const handleMessage = (msg: WsMessage) => {
    switch (msg.type) {
      case 'start':
        addLog(`任务开始 | 模型: ${msg.model} | 最大步数: ${msg.max_steps}`)
        break
      case 'step_start':
        addLog(`Step ${msg.step}: 📍 ${msg.url}`)
        addLog(`  📄 ${msg.title} | ${msg.element_count} 个可交互元素`)
        setLiveStep(msg)
        break
      case 'action':
        addLog(`Step ${msg.step}: 🎯 动作 = ${msg.action}(${JSON.stringify(msg.params)})`)
        setLiveStep(msg)
        break
      case 'step_result':
        if (msg.success) {
          addLog(`Step ${msg.step}: ✅ 成功 (${msg.duration}s)`)
          if (msg.extracted_content) addLog(`  📦 ${msg.extracted_content.substring(0, 120)}`)
        } else {
          addLog(`Step ${msg.step}: ❌ 失败 - ${msg.error}`)
        }
        setSteps(prev => [...prev, {
          step: msg.step || 0,
          url: liveStep?.url || '',
          title: liveStep?.title || '',
          action: liveStep?.action || '',
          params: liveStep?.params || {},
          success: msg.success || false,
          duration: msg.duration || 0,
        }])
        break
      case 'done':
        addLog(`🎉 任务完成 | 状态: ${msg.status}`)
        addLog(`  总步数: ${msg.total_steps} | 总耗时: ${msg.total_duration}s`)
        setSummary({ total: msg.total_steps || 0, duration: msg.total_duration || 0 })
        setStatus('done')
        break
      case 'error':
        addLog(`🔴 错误: ${msg.message}`)
        setStatus('error')
        break
      case 'stopped':
        addLog(`🛑 任务已停止 (Step ${msg.step})`)
        setStatus('stopped')
        break
      case 'max_steps_reached':
        addLog(`⚠️ 达到最大步数限制`)
        break
      case 'warning':
        addLog(`⚠️ ${msg.message}`)
        break
    }
  }

  // 停止任务
  const stopTask = async () => {
    if (taskId) {
      await fetch(`/api/tasks/${taskId}/stop`, { method: 'POST' })
      addLog('已发送停止信号')
    }
    wsRef.current?.close()
    setStatus('stopped')
  }

  const statusColors: Record<RunStatus, string> = {
    idle: 'bg-slate-600',
    connecting: 'bg-yellow-500 animate-pulse',
    running: 'bg-green-500 animate-pulse',
    done: 'bg-blue-500',
    error: 'bg-red-500',
    stopped: 'bg-orange-500',
  }
  const statusLabels: Record<RunStatus, string> = {
    idle: '待机', connecting: '连接中', running: '运行中',
    done: '已完成', error: '出错', stopped: '已停止',
  }

  return (
    <div className="min-h-screen p-4 max-w-7xl mx-auto">
      {/* 标题 */}
      <header className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          🤖 Browser-Use 控制台
        </h1>
        <p className="text-slate-400 text-sm mt-1">AI 浏览器自动化 Agent — 可视化操控</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 左侧: 任务配置 */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-3">📋 任务配置</h2>
            <div className="space-y-3">
              <div>
                <label className="text-sm text-slate-400 mb-1 block">任务描述</label>
                <textarea
                  className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm h-24 resize-none focus:border-blue-500 focus:outline-none"
                  value={task}
                  onChange={e => setTask(e.target.value)}
                  disabled={status === 'running' || status === 'connecting'}
                  placeholder="描述你想让 Agent 完成的任务..."
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">模型</label>
                  <select
                    className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm"
                    value={model}
                    onChange={e => setModel(e.target.value)}
                    disabled={status === 'running'}
                  >
                    <option value="step-1-8k">Step-1-8K (阶跃星辰)</option>
                    <option value="step-1-32k">Step-1-32K (阶跃星辰)</option>
                    <option value="step-1v-8k">Step-1V-8K (阶跃星辰多模态)</option>
                    <option value="gpt-4o">GPT-4o (OpenAI)</option>
                    <option value="gpt-4o-mini">GPT-4o Mini (OpenAI)</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo (OpenAI)</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">最大步数</label>
                  <input
                    type="number"
                    className="w-full bg-slate-900 border border-slate-600 rounded p-2 text-sm"
                    value={maxSteps}
                    onChange={e => setMaxSteps(Number(e.target.value))}
                    disabled={status === 'running'}
                    min={1} max={100}
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={headless}
                  onChange={e => setHeadless(e.target.checked)}
                  disabled={status === 'running'}
                  className="rounded"
                />
                无头模式 (不显示浏览器窗口)
              </label>
            </div>

            <div className="mt-4 flex gap-2">
              <button
                onClick={startTask}
                disabled={status === 'running' || status === 'connecting'}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded transition-colors"
              >
                {status === 'connecting' ? '连接中...' : status === 'running' ? '运行中...' : '▶ 启动任务'}
              </button>
              <button
                onClick={stopTask}
                disabled={status !== 'running' && status !== 'connecting'}
                className="bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white font-medium py-2 px-4 rounded transition-colors"
              >
                ⏹ 停止
              </button>
            </div>

            {/* 状态指示器 */}
            <div className="mt-3 flex items-center gap-2 text-sm">
              <span className={`w-3 h-3 rounded-full ${statusColors[status]}`}></span>
              <span className="text-slate-300">{statusLabels[status]}</span>
              {summary && (
                <span className="text-slate-400 ml-auto">
                  {summary.total} 步 / {summary.duration}s
                </span>
              )}
            </div>
          </div>

          {/* 当前步骤实时状态 */}
          {liveStep && status === 'running' && (
            <div className="bg-slate-800 rounded-lg p-4 border border-blue-600/50">
              <h3 className="text-sm font-semibold text-blue-400 mb-2">⚡ 当前步骤</h3>
              {liveStep.url && <p className="text-xs text-slate-400 truncate">📍 {liveStep.url}</p>}
              {liveStep.title && <p className="text-sm mt-1">📄 {liveStep.title}</p>}
              {liveStep.action && (
                <p className="text-sm mt-2 font-mono text-green-400">
                  🎯 {liveStep.action}({JSON.stringify(liveStep.params)})
                </p>
              )}
            </div>
          )}
        </div>

        {/* 右侧: 步骤列表 + 日志 */}
        <div className="lg:col-span-2 space-y-4">
          {/* 执行步骤时间轴 */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-3">📊 执行步骤 ({steps.length})</h2>
            {steps.length === 0 ? (
              <p className="text-slate-500 text-sm py-4 text-center">暂无步骤, 启动任务后将实时显示...</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {steps.map((s, i) => (
                  <div key={i} className="flex items-start gap-3 p-2 bg-slate-900/50 rounded text-sm">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${s.success ? 'bg-green-600' : 'bg-red-600'}`}>
                      {s.step}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-green-400">{s.action}</span>
                        <span className="text-slate-500 text-xs">{s.duration}s</span>
                      </div>
                      <p className="text-xs text-slate-400 truncate mt-0.5">{s.title || s.url}</p>
                    </div>
                    <span className="text-xs">{s.success ? '✅' : '❌'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 实时日志 */}
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <h2 className="text-lg font-semibold mb-3">📝 实时日志</h2>
            <div className="bg-slate-950 rounded p-3 font-mono text-xs space-y-0.5 max-h-80 overflow-y-auto">
              {logs.length === 0 ? (
                <p className="text-slate-600 text-center py-4">日志将在这里实时显示...</p>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="text-slate-300 whitespace-pre-wrap break-all">
                    {log}
                  </div>
                ))
              )}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      </div>

      {/* 底部说明 */}
      <footer className="mt-6 text-center text-xs text-slate-600">
        Browser-Use 控制台 · Phase 3 · 前端 React + 后端 FastAPI + WebSocket
      </footer>
    </div>
  )
}
