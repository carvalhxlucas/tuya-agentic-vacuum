export type RobotStatus = 'cleaning' | 'docked' | 'idle' | 'error' | 'returning'

export interface RobotState {
  status: RobotStatus
  batteryLevel: number
  lastUpdated: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  actionPayload?: RobotActionPayload
  timestamp: string
}

export interface RobotActionPayload {
  action: string
  parameters?: Record<string, unknown>
  executedAt: string
}

export interface ChatResponse {
  message: string
  actionPayload?: RobotActionPayload
}
