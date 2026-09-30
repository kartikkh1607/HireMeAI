// =============================================================================
// src/api.ts
// Kaam: backend se baat karna. Components ko fetch/stream ki details nahi
// pata honi chahiye - wo bas getProfile() aur streamChat() call karte hain.
// =============================================================================
import type { ChatErrorKind, ChatTurn, Profile } from './types'

// Server history me max 20 messages leta hai (warna 422). Hum sirf aakhri 10
// bhejte hain - follow-up samajhne ke liye kaafi, aur tokens bhi kam jalte hain.
export const MAX_HISTORY = 10

// Server har history message ka content max 4000 chars leta hai
// (app/schemas.py ChatMessage). Lamba jawab history me waapas bhejte waqt
// kaat dete hain - warna agla sawaal 422 pe fail ho jaata.
export const MAX_HISTORY_CONTENT = 4000

// Server jawab ke BEECH me fail ho to stream ke end me ye EXACT string bhejta
// hai. app/main.py ke STREAM_ERROR_SENTINEL se match hona chahiye!
export const STREAM_ERROR_SENTINEL = '\n\n[[HIREMEAI_STREAM_ERROR]]'

// Humari apni error class - UI isse "kind" dekh ke sahi message dikhata hai
export class ChatError extends Error {
  readonly kind: ChatErrorKind
  readonly status?: number
  // Server ka JSON "detail" (agar string ho) - 429 me minute/day ka farak batata hai
  readonly detail?: string

  constructor(kind: ChatErrorKind, message: string, status?: number, detail?: string) {
    super(message)
    this.name = 'ChatError'
    this.kind = kind
    this.status = status
    this.detail = detail
  }
}

export async function getProfile(signal?: AbortSignal): Promise<Profile> {
  const res = await fetch('/profile', { signal })
  if (!res.ok) throw new Error(`GET /profile failed with ${res.status}`)
  return (await res.json()) as Profile
}

interface StreamChatOptions {
  question: string
  history: ChatTurn[]
  // Har naya tukda (chunk) aate hi ye call hota hai -> UI turant update
  onChunk: (text: string) => void
  // AbortController.signal - Stop button isse request beech me kaat deta hai
  signal?: AbortSignal
}

// Error response ka {"detail": "..."} padhna. FastAPI 422 me detail ek LIST
// hoti hai (technical) - wo user ko nahi dikhate, sirf string wali.
async function readDetail(res: Response): Promise<string | undefined> {
  try {
    const body: unknown = await res.json()
    if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // JSON nahi tha - koi baat nahi
  }
  return undefined
}

// Text ke END me sentinel ka shuruaati hissa hai? (jaise "...\n\n[[HIRE")
// Wo hissa abhi UI ko nahi dikhana - ho sakta hai agle chunk me baaki sentinel aaye.
function sentinelPrefixAtEnd(text: string): number {
  for (let k = Math.min(text.length, STREAM_ERROR_SENTINEL.length - 1); k > 0; k--) {
    if (text.endsWith(STREAM_ERROR_SENTINEL.slice(0, k))) return k
  }
  return 0
}

// POST /chat -> jawab text/plain STREAM me aata hai (poora ek saath nahi).
// Resolve = jawab poora aa gaya. Reject = ChatError, ya AbortError (Stop dabaya).
export async function streamChat({ question, history, onChunk, signal }: StreamChatOptions) {
  // .slice(-10) = array ke AAKHRI 10 items (purane wale chhod do)
  const recent = history.slice(-MAX_HISTORY).map((turn) => ({
    role: turn.role,
    content: turn.content.slice(0, MAX_HISTORY_CONTENT),
  }))

  let res: Response
  try {
    res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history: recent }),
      signal,
    })
  } catch (err) {
    // Stop dabaya -> ye asli error nahi hai, AbortError aage jaane do
    if (signal?.aborted) throw err
    // fetch sirf tab throw karta hai jab server tak pahunche hi nahi (offline, server band)
    throw new ChatError('network', 'Could not reach the server')
  }

  // Dhyaan do: fetch 4xx/5xx pe throw NAHI karta, khud check karna padta hai
  if (!res.ok || !res.body) {
    const detail = await readDetail(res)
    if (res.status === 422) throw new ChatError('validation', 'Invalid question', 422)
    if (res.status === 429) throw new ChatError('rate_limit', 'Rate limited', 429, detail)
    if (res.status === 503) throw new ChatError('unavailable', 'Service unavailable', 503, detail)
    throw new ChatError('server', `Server error (${res.status})`, res.status)
  }

  // ---------------------------------------------------------------------------
  // STREAMING READER
  // res.body ek ReadableStream hai. getReader() se hum tukde ek-ek karke padhte
  // hain, jaise-jaise server bhejta hai (res.text() poore jawab ka wait karta).
  // Tukde BYTES (Uint8Array) me aate hain, text me badalne ke liye TextDecoder.
  //
  // {stream: true} kyun? UTF-8 me ek character 1-4 bytes ka hota hai (jaise
  // "–" ya emoji). Network kabhi character ko do tukdon me kaat deta hai.
  // stream:true bolta hai "adhure bytes yaad rakho, agle tukde ke saath jodo"
  // - warna beech me "�" jaise kachre characters dikhte.
  //
  // SENTINEL: network sentinel ko bhi do tukdon me kaat sakta hai
  // ("...\n\n[[HIRE" + "MEAI_STREAM_ERROR]]"). Isliye "pending" me text ka
  // wo end rok ke rakhte hain jo sentinel ki shuruaat jaisa dikhe.
  // ---------------------------------------------------------------------------
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''

  // pending me naya text jodo; sentinel mila to error, warna safe hissa UI ko do
  const push = (text: string) => {
    pending += text
    const at = pending.indexOf(STREAM_ERROR_SENTINEL)
    if (at !== -1) {
      if (at > 0) onChunk(pending.slice(0, at))
      pending = ''
      throw new ChatError('interrupted', 'The answer was interrupted')
    }
    const hold = sentinelPrefixAtEnd(pending)
    const safe = pending.slice(0, pending.length - hold)
    if (safe) onChunk(safe)
    pending = pending.slice(pending.length - hold)
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      push(decoder.decode(value, { stream: true }))
    }
    // Aakhri flush - decoder ke bache bytes + roka hua text (sentinel nahi nikla)
    push(decoder.decode())
    if (pending) onChunk(pending)
  } catch (err) {
    if (err instanceof ChatError) throw err
    if (signal?.aborted) throw err
    // Stream beech me toota (wifi gaya, server restart)
    throw new ChatError('network', 'Connection lost while streaming')
  } finally {
    reader.releaseLock()
  }
}
