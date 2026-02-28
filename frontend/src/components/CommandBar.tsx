import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mic, Loader2, Sparkles } from 'lucide-react'
import { sendChatCommand } from '../services/api'
import type { ChatMessage, RobotActionPayload } from '../types/robot'

interface CommandBarProps {
  onActionExecuted?: (payload: RobotActionPayload) => void
  isProcessing?: boolean
  onProcessingChange?: (value: boolean) => void
}

export function CommandBar({ onActionExecuted, onProcessingChange }: CommandBarProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isProcessing, setProcessing] = useState(false)

  const updateProcessing = useCallback(
    (value: boolean) => {
      setProcessing(value)
      onProcessingChange?.(value)
    },
    [onProcessingChange]
  )

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      const text = input.trim()
      if (!text || isProcessing) return

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMessage])
      setInput('')
      updateProcessing(true)

      try {
        const res = await sendChatCommand(text)
        const assistantMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: res.message,
          actionPayload: res.actionPayload,
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMessage])
        if (res.actionPayload) onActionExecuted?.(res.actionPayload)
      } catch (err) {
        const errorMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Erro ao processar comando.',
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, errorMessage])
      } finally {
        updateProcessing(false)
      }
    },
    [input, isProcessing, onActionExecuted, updateProcessing]
  )

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="glass-panel flex flex-col flex-1 min-h-0 overflow-hidden"
    >
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-neon-purple" />
        <span className="text-sm text-gray-400">O que o robô deve fazer agora?</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[120px]">
        <AnimatePresence mode="popLayout">
          {messages.length === 0 && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-gray-500 text-center py-4"
            >
              Digite ou fale um comando. Ex: &quot;Limpe a cozinha&quot;, &quot;Volte para a base&quot;
            </motion.p>
          )}
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-4 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-neon-blue/20 text-neon-blue border border-neon-blue/30'
                    : 'bg-white/5 text-gray-200 border border-white/10'
                }`}
              >
                {msg.content}
              </div>
            </motion.div>
          ))}
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2 text-neon-purple text-sm"
            >
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Processando...</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <form onSubmit={handleSubmit} className="p-4 border-t border-white/10">
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Comando em linguagem natural..."
            disabled={isProcessing}
            className="flex-1 bg-void-800/80 border border-white/10 rounded-xl px-4 py-3 text-sm placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-neon-purple/50 focus:border-neon-purple/50 transition-all"
          />
          <button
            type="button"
            className="p-3 rounded-xl glass-panel glass-panel-hover text-gray-400 hover:text-neon-purple"
            aria-label="Falar"
          >
            <Mic className="w-5 h-5" />
          </button>
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="p-3 rounded-xl bg-neon-purple/20 border border-neon-purple/40 text-neon-purple hover:bg-neon-purple/30 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </motion.div>
  )
}
