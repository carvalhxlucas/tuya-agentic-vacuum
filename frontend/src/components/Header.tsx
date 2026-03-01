import { motion } from 'framer-motion'
import { Battery, AlertCircle, Home, Loader2, CheckCircle } from 'lucide-react'
import type { RobotStatus } from '../types/robot'

const statusConfig: Record<RobotStatus, { label: string; icon: typeof Home; color: string }> = {
  cleaning: { label: 'Cleaning', icon: Loader2, color: 'text-neon-cyan' },
  docked: { label: 'Docked', icon: Home, color: 'text-emerald-400' },
  idle: { label: 'Idle', icon: CheckCircle, color: 'text-gray-400' },
  error: { label: 'Error', icon: AlertCircle, color: 'text-red-400' },
  returning: { label: 'Returning', icon: Loader2, color: 'text-neon-purple' },
}

interface HeaderProps {
  status: RobotStatus
  batteryLevel: number
}

export function Header({ status, batteryLevel }: HeaderProps) {
  const config = statusConfig[status]
  const Icon = config.icon
  const circumference = 2 * Math.PI * 18
  const strokeDashoffset = circumference - (batteryLevel / 100) * circumference

  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel px-4 py-3 flex items-center justify-between"
    >
      <div className="flex items-center gap-3">
        <div className={`flex items-center gap-2 ${config.color}`}>
          <Icon className={status === 'cleaning' || status === 'returning' ? 'animate-spin w-5 h-5' : 'w-5 h-5'} />
          <span className="font-medium text-sm">{config.label}</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Battery</span>
        <div className="relative w-10 h-10">
          <svg className="w-10 h-10 -rotate-90" viewBox="0 0 40 40">
            <circle
              cx="20"
              cy="20"
              r="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              className="text-void-700"
            />
            <motion.circle
              cx="20"
              cy="20"
              r="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              className={batteryLevel > 20 ? 'text-neon-blue' : 'text-red-400'}
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 0.5 }}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[10px] font-semibold">
            {batteryLevel}%
          </span>
        </div>
      </div>
    </motion.header>
  )
}
