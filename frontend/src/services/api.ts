import type { ChatResponse, RobotState, RobotStatus } from '../types/robot'

const VALID_STATUSES: RobotStatus[] = ['cleaning', 'docked', 'idle', 'error', 'returning']

function parseRobotStatus(value: unknown): RobotStatus {
  if (typeof value === 'string' && VALID_STATUSES.includes(value as RobotStatus)) {
    return value as RobotStatus
  }
  return 'idle'
}

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

export async function sendChatCommand(command: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: command }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? 'Falha ao processar comando')
  }
  return res.json()
}

export async function getRobotState(): Promise<RobotState> {
  const res = await fetch(`${API_BASE}/robot/state`)
  if (!res.ok) {
    throw new Error('Falha ao obter estado do robô')
  }
  const data = await res.json()
  return {
    status: parseRobotStatus(data.status),
    batteryLevel: typeof data.batteryLevel === 'number' ? Math.max(0, Math.min(100, data.batteryLevel)) : 0,
    lastUpdated: new Date().toISOString(),
  }
}
