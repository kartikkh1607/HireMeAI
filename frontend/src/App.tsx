// =============================================================================
// App.tsx - poori chat ka "dimaag": messages ki list, profile, streaming.
// Components sirf dikhate hain; data aur logic yahan hai.
//
// History sirf BROWSER me (is state me) rehti hai. Server stateless hai -
// har /chat request ke saath hum khud pichhli baatein bhejte hain.
// Page refresh ya "New chat" = nayi conversation.
// =============================================================================
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ChatError, getProfile, streamChat } from './api'
import { Composer } from './components/Composer'
import { EmptyState } from './components/EmptyState'
import { MessageList } from './components/MessageList'
import { TopBar } from './components/TopBar'
import { detectProfileLinks, initials } from './lib/profile'
import type { ChatTurn, Profile, UIMessage } from './types'

const newId = () => crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`

// -----------------------------------------------------------------------------
// HISTORY BANANA
// Server ko sirf "poore" sawaal-jawab pairs bhejo:
//   - jis sawaal ka jawab error me gaya, wo pair skip (galat context na jaaye)
//   - khali jawab (Stop jaldi daba diya) skip
//   - Stop ke baad ka ADHURA jawab bhej sakte hain - user ne wahi dekha hai
// Aakhri 10 ka slice api.ts me hota hai (MAX_HISTORY).
// -----------------------------------------------------------------------------
function buildHistory(messages: UIMessage[]): ChatTurn[] {
  const turns: ChatTurn[] = []
  for (let i = 0; i < messages.length - 1; i++) {
    const question = messages[i]
    const answer = messages[i + 1]
    if (question.role !== 'user' || answer.role !== 'assistant') continue
    if (answer.status === 'error' || answer.status === 'streaming' || !answer.content.trim()) continue
    turns.push({ role: 'user', content: question.content }, { role: 'assistant', content: answer.content })
    i++
  }
  return turns
}

export default function App() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [messages, setMessages] = useState<UIMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const [chatKey, setChatKey] = useState(0)

  // Chal rahi request ka AbortController. Ref me kyunki ye UI nahi badalta,
  // bas Stop / New chat ko isse abort() karna hota hai.
  const abortRef = useRef<AbortController | null>(null)
  // Latest messages ref me bhi - taaki async callbacks purana (stale) data na padhein
  const messagesRef = useRef(messages)
  messagesRef.current = messages

  useEffect(() => {
    const controller = new AbortController()
    getProfile(controller.signal)
      .then(setProfile)
      .catch(() => {
        // Profile na mile to bhi chat chale - naam ki jagah generic text
      })
    return () => controller.abort()
  }, [])

  const links = useMemo(() => detectProfileLinks(profile?.links ?? []), [profile])
  const avatarLabel = initials(profile?.name)

  // Ek assistant message ko update karne ka chhota helper
  const patch = useCallback((id: string, fn: (m: UIMessage) => UIMessage) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)))
  }, [])

  // Jawab stream karke assistant message (id) me bharna
  const runAnswer = useCallback(
    async (assistantId: string, question: string, history: ChatTurn[]) => {
      // -----------------------------------------------------------------------
      // ABORT CONTROLLER
      // Har request ka apna controller. controller.abort() dabate hi fetch /
      // reader.read() ek AbortError throw karte hain aur network request band.
      // Jo text ab tak aa chuka wo state me hai -> partial jawab bach jaata hai.
      // -----------------------------------------------------------------------
      const controller = new AbortController()
      abortRef.current = controller
      setStreaming(true)

      try {
        await streamChat({
          question,
          history,
          signal: controller.signal,
          onChunk: (text) => patch(assistantId, (m) => ({ ...m, content: m.content + text })),
        })
        patch(assistantId, (m) => ({ ...m, status: 'done' }))
      } catch (err) {
        if (controller.signal.aborted) {
          patch(assistantId, (m) => ({ ...m, status: 'stopped' }))
        } else {
          const kind = err instanceof ChatError ? err.kind : 'network'
          patch(assistantId, (m) => ({ ...m, status: 'error', error: kind }))
        }
      } finally {
        // Sirf apna hi controller saaf karo (New chat ke baad naya chal raha ho sakta hai)
        if (abortRef.current === controller) {
          abortRef.current = null
          setStreaming(false)
        }
      }
    },
    [patch],
  )

  const send = useCallback(
    (question: string) => {
      if (abortRef.current) return // ek waqt me ek hi jawab
      const history = buildHistory(messagesRef.current)
      const assistantId = newId()
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: 'user', content: question, status: 'done' },
        { id: assistantId, role: 'assistant', content: '', status: 'streaming' },
      ])
      void runAnswer(assistantId, question, history)
    },
    [runAnswer],
  )

  // Retry: error wale jawab ko khaali karke wahi sawaal, WAHI purani history ke saath
  const retry = useCallback(
    (assistantId: string) => {
      if (abortRef.current) return
      const all = messagesRef.current
      const index = all.findIndex((m) => m.id === assistantId)
      const question = all[index - 1]
      if (index < 1 || question.role !== 'user') return
      const history = buildHistory(all.slice(0, index - 1))
      patch(assistantId, (m) => ({ ...m, content: '', status: 'streaming', error: undefined }))
      void runAnswer(assistantId, question.content, history)
    },
    [patch, runAnswer],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  const newChat = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setStreaming(false)
    setMessages([])
    setChatKey((k) => k + 1)
  }, [])

  const name = profile?.name ?? null
  const isEmpty = messages.length === 0

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <TopBar name={name} links={links} canReset={!isEmpty} onNewChat={newChat} />

      <main className="flex min-h-0 flex-1 flex-col">
        {isEmpty ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
            <EmptyState name={name} onPick={send} />
          </div>
        ) : (
          <MessageList messages={messages} avatarLabel={avatarLabel} busy={streaming} onRetry={retry} />
        )}
      </main>

      <footer className="shrink-0 pt-1 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <Composer streaming={streaming} onSend={send} onStop={stop} focusKey={chatKey} />
        <p className="mt-2 px-4 text-center text-xs text-subtle">
          AI assistant - answers come only from the resume and can contain mistakes.
        </p>
      </footer>
    </div>
  )
}
