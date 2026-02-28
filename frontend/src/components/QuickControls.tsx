import { motion } from 'framer-motion'
import { Play, Pause, Home, MapPin } from 'lucide-react'

const controls = [
  { id: 'start', label: 'Iniciar', icon: Play, action: 'start_cleaning' },
  { id: 'pause', label: 'Pausar', icon: Pause, action: 'stop_cleaning' },
  { id: 'base', label: 'Voltar à base', icon: Home, action: 'return_to_base' },
  { id: 'locate', label: 'Localizar', icon: MapPin, action: 'locate' },
] as const

interface QuickControlsProps {
  onQuickAction?: (action: string) => void
  isProcessing?: boolean
}

export function QuickControls({ onQuickAction, isProcessing }: QuickControlsProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="grid grid-cols-4 gap-3"
    >
      {controls.map(({ id, label, icon: Icon, action }, i) => (
        <motion.button
          key={id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 * i }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => !isProcessing && onQuickAction?.(action)}
          disabled={isProcessing}
          className="glass-panel glass-panel-hover flex flex-col items-center justify-center py-4 px-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Icon className="w-6 h-6 text-neon-blue mb-2" />
          <span className="text-xs text-gray-400 font-medium text-center">{label}</span>
        </motion.button>
      ))}
    </motion.div>
  )
}
