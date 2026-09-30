// =============================================================================
// src/api.ts
// Kaam: backend se baat karna. Components ko fetch/stream ki details nahi
// pata honi chahiye - wo bas getProfile() aur streamChat() call karte hain.
// =============================================================================
import type { ChatErrorKind, ChatTurn, Profile } from './types'

// Server history me max 20 messages leta hai (warna 422). Hum sirf aakhri 10
// bhejte hain - follow-up samajhne ke liye kaafi, aur tokens bhi kam jalte hain.
export const MAX_HISTORY = 10

// Humari apni error class - UI isse "kind" dekh ke sahi message dikhata hai
export class ChatError extends Error {
  readonly kind: ChatErrorKind
  readonly status?: number

  constructor(kind: ChatErrorKind, message: string, status?: number) {
    super(message)
    this.name = 'ChatError'
    this.kind = kind
    this.status = status
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

// POST /chat -> jawab text/plain STREAM me aata hai (poora ek saath nahi).
// Resolve = jawab poora aa gaya. Reject = ChatError, ya AbortError (Stop dabaya).
export async function streamChat({ question, history, onChunk, signal }: StreamChatOptions) {
  let res: Response
  try {
    res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      // .slice(-10) = array ke AAKHRI 10 items (purane wale chhod do)
      body: JSON.stringify({ question, history: history.slice(-MAX_HISTORY) }),
      signal,
    })
  } catch (err) {
    // Stop dabaya -> ye asli error nahi hai, AbortError aage jaane do
    if (signal?.aborted) throw err
    // fetch sirf tab throw karta hai jab server tak pahunche hi nahi (offline, server band)
    throw new ChatError('network', 'Could not reach the server')
  }

  // Dhyaan do: fetch 4xx/5xx pe throw NAHI karta, khud check karna padta hai
  if (res.status === 422) {
    throw new ChatError('validation', 'That question could not be processed', 422)
  }
  if (!res.ok || !res.body) {
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
  // ---------------------------------------------------------------------------
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      if (text) onChunk(text)
    }
    // Aakhri flush - agar koi bytes decoder ke paas bache hon
    const tail = decoder.decode()
    if (tail) onChunk(tail)
  } catch (err) {
    if (signal?.aborted) throw err
    // Stream beech me toota (wifi gaya, server restart)
    throw new ChatError('network', 'Connection lost while streaming')
  } finally {
    reader.releaseLock()
  }
}
