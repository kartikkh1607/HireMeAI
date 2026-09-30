import { ArrowUp, Square } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'

// Server ChatRequest.question max 1000 chars leta hai - UI bhi wahi limit rakhe
export const MAX_QUESTION = 1000
const COUNTER_FROM = 800 // counter sirf limit ke paas dikhe, warna distraction
const MAX_HEIGHT_PX = 200

interface ComposerProps {
  streaming: boolean
  onSend: (question: string) => void
  onStop: () => void
  // Parent ye badle (New chat) to textarea pe focus wapas
  focusKey: number
}

export function Composer({ streaming, onSend, onStop, focusKey }: ComposerProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const trimmed = value.trim()
  const canSend = trimmed.length > 0 && !streaming

  // AUTO-GROW: height ko 'auto' karke scrollHeight (asli content ki height)
  // naapo, phir max 200px tak utni height de do. Usse zyada -> andar scroll.
  useLayoutEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`
  }, [value])

  // Desktop pe focus; mobile (touch) pe nahi - warna keyboard khud khul jaata
  useEffect(() => {
    if (window.matchMedia('(pointer: fine)').matches) textareaRef.current?.focus()
  }, [focusKey])

  function submit() {
    if (!canSend) return
    onSend(trimmed)
    setValue('')
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    submit()
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // IME (Hindi/Japanese keyboards): word choose karte waqt Enter dabta hai -
    // us waqt isComposing true hota hai, tab message mat bhejo.
    // keyCode 229 = kuch purane browsers ka IME signal.
    if (e.nativeEvent.isComposing || e.keyCode === 229) return
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault() // nayi line mat daalo
      submit()
    }
  }

  const count = value.length
  const showCounter = count >= COUNTER_FROM

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[760px] px-3 sm:px-6">
      <div className="flex items-end gap-2 rounded-[26px] border border-border bg-surface p-2 pl-4 shadow-[0_1px_12px_-4px_rgb(0_0_0/0.25)] transition-colors focus-within:border-subtle">
        <label htmlFor="question" className="sr-only">
          Ask a question about the candidate
        </label>
        <textarea
          id="question"
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={MAX_QUESTION}
          rows={1}
          placeholder="Ask about projects, skills…"
          aria-describedby={showCounter ? 'question-count' : undefined}
          // text-base (16px) -> iPhone input pe zoom nahi karta
          className="max-h-[200px] min-h-10 flex-1 resize-none bg-transparent py-2 text-base leading-6 text-fg placeholder:text-subtle focus:outline-none"
        />

        <div className="flex shrink-0 items-center gap-2">
          {showCounter && (
            <span
              id="question-count"
              className={`text-xs tabular-nums ${count >= MAX_QUESTION ? 'text-danger' : 'text-subtle'}`}
            >
              {count}/{MAX_QUESTION}
            </span>
          )}

          {streaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop generating"
              title="Stop"
              className="grid size-9 place-items-center rounded-full bg-fg text-bg transition-opacity hover:opacity-85"
            >
              <Square size={13} fill="currentColor" aria-hidden="true" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send message"
              title="Send"
              className="grid size-9 place-items-center rounded-full bg-fg text-bg transition-opacity hover:opacity-85 disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-subtle disabled:hover:opacity-100"
            >
              <ArrowUp size={18} strokeWidth={2.25} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
    </form>
  )
}
