import { ArrowDown } from 'lucide-react'
import { useLayoutEffect, useRef, useState } from 'react'
import type { UIMessage } from '../types'
import { Message } from './Message'

// Bottom se itne px ke andar ho to "neeche hi hai" maante hain
const NEAR_BOTTOM_PX = 96

interface MessageListProps {
  messages: UIMessage[]
  avatarLabel: string
  busy: boolean
  onRetry: (id: string) => void
}

export function MessageList({ messages, avatarLabel, busy, onRetry }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  // useRef (state nahi) kyunki har scroll event pe re-render nahi chahiye
  const stickToBottom = useRef(true)
  const prevCount = useRef(0)
  const [showJump, setShowJump] = useState(false)

  // ---------------------------------------------------------------------------
  // AUTO-SCROLL LOGIC
  // Jawab stream ho raha hai aur user neeche hai -> saath-saath neeche scroll.
  // Par agar user UPAR scroll karke purana jawab padh raha hai, to use zabardasti
  // neeche mat kheecho (bahut irritating hota hai). Isliye:
  //   - har scroll pe check: user bottom ke paas hai? -> stickToBottom
  //   - naya message aaya (user ne bheja) -> hamesha neeche jao
  //   - sirf content bada hua (streaming) -> tabhi neeche jao jab stick ho
  // useLayoutEffect -> browser paint se PEHLE scroll, warna jhatka (flicker) dikhta.
  // ---------------------------------------------------------------------------
  function handleScroll() {
    const el = scrollRef.current
    if (!el) return
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight
    stickToBottom.current = distance < NEAR_BOTTOM_PX
    setShowJump(!stickToBottom.current)
  }

  useLayoutEffect(() => {
    const el = scrollRef.current
    if (!el) return
    if (messages.length > prevCount.current) stickToBottom.current = true
    prevCount.current = messages.length
    if (stickToBottom.current) el.scrollTop = el.scrollHeight
  }, [messages])

  function jumpToBottom() {
    const el = scrollRef.current
    if (!el) return
    stickToBottom.current = true
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={scrollRef} onScroll={handleScroll} className="h-full overflow-x-hidden overflow-y-auto">
        <div
          role="log"
          aria-live="polite"
          // aria-busy -> screen reader har chunk pe bolna shuru na kare, poora jawab aane de
          aria-busy={busy}
          aria-label="Conversation"
          className="mx-auto flex w-full max-w-[760px] flex-col gap-7 px-4 pt-6 pb-10 sm:px-6"
        >
          {messages.map((m) => (
            <Message key={m.id} message={m} avatarLabel={avatarLabel} onRetry={onRetry} />
          ))}
        </div>
      </div>

      {showJump && (
        <button
          type="button"
          onClick={jumpToBottom}
          aria-label="Scroll to latest message"
          className="fade-in absolute bottom-3 left-1/2 grid size-9 -translate-x-1/2 place-items-center rounded-full border border-border bg-bg text-muted shadow-lg transition-colors hover:text-fg"
        >
          <ArrowDown size={17} aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
