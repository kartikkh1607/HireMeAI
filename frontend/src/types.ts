// Backend ke GET /profile ka shape (app/schemas.py ka Resume, bina phone ke).
// Sirf wahi fields likhi hain jo UI me kaam aati hain + contract wali.
export interface Project {
  name: string
  description: string | null
  highlights: string[]
  tech_stack: string[]
  link: string | null
}

export interface Profile {
  name: string | null
  email: string | null
  location: string | null
  summary: string | null
  skills: string[]
  projects: Project[]
  education: unknown[]
  certifications: string[]
  achievements: string[]
  links: string[]
}

// Server ko jaane wala history item (app/schemas.py ka ChatMessage)
export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export type ChatErrorKind = 'validation' | 'network' | 'server'

// UI ka message - ChatTurn + display ki extra info (status, error)
export interface UIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  // streaming = abhi aa raha hai, stopped = user ne Stop dabaya,
  // error = request fail hui (content me partial jawab ho sakta hai)
  status: 'streaming' | 'done' | 'stopped' | 'error'
  error?: ChatErrorKind
}
