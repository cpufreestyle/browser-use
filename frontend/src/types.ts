/** 前端类型定义 */

export type MessageType =
  | 'start'        // 任务开始
  | 'step_start'   // 单步开始 (页面状态)
  | 'action'       // LLM 决策的动作
  | 'step_result'  // 动作执行结果
  | 'warning'      // 警告
  | 'done'         // 任务完成
  | 'error'        // 错误
  | 'stopped'      // 被手动停止
  | 'max_steps_reached' // 达到最大步数

export interface WsMessage {
  type: MessageType
  step?: number
  url?: string
  title?: string
  element_count?: number
  action?: string
  params?: Record<string, unknown>
  llm_response?: string
  success?: boolean
  extracted_content?: string
  error?: string
  message?: string
  duration?: number
  status?: string
  total_steps?: number
  total_duration?: number
  history?: StepRecord[]
  task?: string
  model?: string
  max_steps?: number
}

export interface StepRecord {
  step: number
  url: string
  title: string
  action: string
  params: Record<string, unknown>
  success: boolean
  duration: number
}

export type RunStatus = 'idle' | 'connecting' | 'running' | 'done' | 'error' | 'stopped'
