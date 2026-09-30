import { Check, Copy, RotateCcw, TriangleAlert } from 'lucide-react'
import { memo, useEffect, useRef, useState } from 'react'
import type { ChatErrorKind, UIMessage } from '../types'
import { Avatar } from './Avatar'
import { Markdown } from './Markdown'

const ERROR_TEXT: Record<ChatErrorKind, string> = {
  validation: 'That question could not be processed.',
  network: 'Could not reach the server.',
  server: 'The server ran into a problem.',
}

interface MessageProps {
  message: UIMessage
  avatarLabel: string
  onRetry: (id: string) => void
}

// memo -> streaming ke waqt sirf AAKHRI message re-render hota hai,
// baaki messages ka object same rehta hai to React unhe skip kar deta hai
export const Message = memo(function Message({ message, avatarLabel, onRetry }: MessageProps) {
  if (message.role === 'user') {
    return (
      <div className="fade-in flex justify-end">
        <div className="max-w-[85%] rounded-3xl bg-surface-2 px-4 py-2.5 text-[15px] leading-relaxed break-words whitespace-pre-wrap sm:max-w-[75%]">
          {message.content}
        </div>
      </div>
    )
  }

  const { content, status, error } = message
  const streaming = status === 'streaming'
  const waiting = streaming && content.length === 0

  return (
    <div className="fade-in flex gap-3 sm:gap-4">
      <div className="pt-0.5">
        <Avatar label={avatarLabel} />
      </div>

      <div className="min-w-0 flex-1">
        {waiting ? (
          <ThinkingDots />
        ) : (
          content && <Markdown content={content} streaming={streaming} />
        )}

        {status === 'stopped' && (
          <p className="mt-2 text-[13px] text-subtle italic">{content ? 'Stopped' : 'Response stopped.'}</p>
        )}

        {status === 'error' && error && (
          <div
            role="alert"
            className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-danger/25 bg-danger-soft px-3.5 py-2.5 text-sm"
          >
            <TriangleAlert size={16} aria-hidden="true" className="shrink-0 text-danger" />
            <span className="flex-1">{ERROR_TEXT[error]}</span>
            <button
              type="button"
              onClick={() => onRetry(message.id)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg px-2.5 py-1 text-[13px] font-medium transition-colors hover:bg-surface-2"
            >
              <RotateCcw size={13} aria-hidden="true" />
              Retry
            </button>
          </div>
        )}

        {!streaming && content && (
          <div className="mt-1.5 -ml-1.5 flex">
            <CopyButton text={content} />
          </div>
        )}
      </div>
    </div>
  )
})

function ThinkingDots() {
  return (
    <div role="status" aria-label="Assistant is thinking" className="flex h-7 items-center gap-1">
      <span className="thinking-dot size-1.5 rounded-full bg-muted" />
      <span className="thinking-dot size-1.5 rounded-full bg-muted" />
      <span className="thinking-dot size-1.5 rounded-full bg-muted" />
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => () => window.clearTimeout(timer.current), [])

  async function copy() {
    try {
      await copyText(text)
      setCopied(true)
      window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setCopied(false), 1600)
    } catch {
      // clipboard block ho gaya - chup-chaap ignore, UI na tode
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? 'Copied' : 'Copy response'}
      className="inline-flex h-7 items-center gap-1.5 rounded-md px-1.5 text-xs text-subtle transition-colors hover:bg-surface-2 hover:text-fg"
    >
      {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
      <span aria-live="polite">{copied ? 'Copied' : 'Copy'}</span>
    </button>
  )
}

// navigator.clipboard sirf "secure context" (https ya localhost) me chalta hai.
// Plain http deploy pe purana textarea + execCommand wala tareeka fallback.
async function copyText(text: string) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text)
  }
  const el = document.createElement('textarea')
  el.value = text
  el.setAttribute('readonly', '')
  el.style.position = 'fixed'
  el.style.opacity = '0'
  document.body.appendChild(el)
  el.select()
  const ok = document.execCommand('copy')
  el.remove()
  if (!ok) throw new Error('copy failed')
}
