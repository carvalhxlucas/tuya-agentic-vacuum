import { useState, useCallback, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Header } from './Header'
import { CommandBar } from './CommandBar'
import { QuickControls } from './QuickControls'
import { getRobotState } from '../services/api'
import type { RobotStatus } from '../types/robot'
import type { RobotActionPayload } from '../types/robot'

const POLL_INTERVAL_MS = 10000

export function Dashboard() {
  const [status, setStatus] = useState<RobotStatus>('docked')
  const [batteryLevel, setBatteryLevel] = useState(0)
  const [isProcessing, setProcessing] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchRobotState = useCallback(async () => {
    try {
      const state = await getRobotState()
      setStatus(state.status)
      setBatteryLevel(state.batteryLevel)
    } catch {
      setStatus('idle')
      setBatteryLevel(0)
    }
  }, [])

  useEffect(() => {
    fetchRobotState()
    pollRef.current = setInterval(fetchRobotState, POLL_INTERVAL_MS)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [fetchRobotState])

  const handleActionExecuted = useCallback((payload: RobotActionPayload) => {
    const action = payload.action
    if (action === 'start_cleaning') setStatus('cleaning')
    if (action === 'stop_cleaning') setStatus('idle')
    if (action === 'return_to_base') setStatus('returning')
    fetchRobotState()
  }, [fetchRobotState])

  const handleQuickAction = useCallback(async (action: string) => {
    try {
      setProcessing(true)
      const baseUrl = import.meta.env.VITE_API_URL ?? '/api'
      const res = await fetch(`${baseUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: action === 'start_cleaning' ? 'Iniciar limpeza' : action === 'stop_cleaning' ? 'Parar' : action === 'return_to_base' ? 'Voltar para a base' : 'Localizar o robô',
        }),
      })
      const data = await res.json()
      if (data.actionPayload) handleActionExecuted(data.actionPayload)
    } finally {
      setProcessing(false)
    }
  }, [handleActionExecuted])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex flex-col p-4 gap-4 max-w-lg mx-auto pb-8 safe-area-padding"
    >
      <Header status={status} batteryLevel={batteryLevel} />
      <div className="flex-1 flex flex-col min-h-0">
        <CommandBar
          onActionExecuted={handleActionExecuted}
          isProcessing={isProcessing}
          onProcessingChange={setProcessing}
        />
      </div>
      <QuickControls onQuickAction={handleQuickAction} isProcessing={isProcessing} />
    </motion.div>
  )
}
