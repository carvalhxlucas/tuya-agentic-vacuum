import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Header } from './Header'
import { CommandBar } from './CommandBar'
import { QuickControls } from './QuickControls'
import type { RobotStatus } from '../types/robot'
import type { RobotActionPayload } from '../types/robot'

const initialBattery = 78
const initialStatus: RobotStatus = 'docked'

export function Dashboard() {
  const [status, setStatus] = useState<RobotStatus>(initialStatus)
  const [batteryLevel, setBatteryLevel] = useState(initialBattery)
  const [isProcessing, setProcessing] = useState(false)

  const handleActionExecuted = useCallback((payload: RobotActionPayload) => {
    const action = payload.action
    if (action === 'start_cleaning') setStatus('cleaning')
    if (action === 'stop_cleaning') setStatus('idle')
    if (action === 'return_to_base') setStatus('returning')
  }, [])

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
