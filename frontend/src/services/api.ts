import type { ChatResponse } from '../types/robot'

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
