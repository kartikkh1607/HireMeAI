// Profile se chhote kaam: initials, first name, aur top bar ke links pehchanna.

export type LinkKind = 'linkedin' | 'github' | 'leetcode' | 'portfolio'

export interface ProfileLink {
  kind: LinkKind
  label: string
  url: string
}

const LABELS: Record<LinkKind, string> = {
  linkedin: 'LinkedIn',
  github: 'GitHub',
  leetcode: 'LeetCode',
  portfolio: 'Portfolio',
}

// SECURITY: sirf http/https URLs chalenge. "javascript:alert(1)" jaisa link
// resume/LLM se aa bhi jaaye to button ban hi nahi payega.
// new URL() relative ya kharab URL pe throw karta hai -> null.
export function safeHttpUrl(href: string | null | undefined): string | null {
  if (!href) return null
  try {
    const url = new URL(href)
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null
  } catch {
    return null
  }
}

function hostMatches(host: string, domain: string) {
  return host === domain || host.endsWith(`.${domain}`)
}

// profile.links me profile links + project repos sab mixed hote hain.
// GitHub PROFILE = github.com/<username> (sirf 1 path segment).
// github.com/<user>/<repo> project hai, top bar me nahi chahiye.
export function detectProfileLinks(links: string[]): ProfileLink[] {
  const found = new Map<LinkKind, string>()

  for (const raw of links) {
    const safe = safeHttpUrl(raw)
    if (!safe) continue
    const url = new URL(safe)
    const host = url.hostname.toLowerCase()
    const segments = url.pathname.split('/').filter(Boolean)

    let kind: LinkKind | null = null
    if (hostMatches(host, 'linkedin.com')) kind = 'linkedin'
    else if (hostMatches(host, 'leetcode.com')) kind = 'leetcode'
    else if (host === 'github.com') kind = segments.length === 1 ? 'github' : null
    else kind = 'portfolio' // baaki koi bhi site = portfolio (pehli wali jeetegi)

    if (kind && !found.has(kind)) found.set(kind, safe)
  }

  const order: LinkKind[] = ['linkedin', 'github', 'leetcode', 'portfolio']
  return order
    .filter((kind) => found.has(kind))
    .map((kind) => ({ kind, label: LABELS[kind], url: found.get(kind)! }))
}

export function initials(name: string | null | undefined): string {
  if (!name) return 'AI'
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : parts[0]?.slice(0, 2)
  return (letters || 'AI').toUpperCase()
}

export function firstName(name: string | null | undefined): string {
  return name?.trim().split(/\s+/)[0] || 'the candidate'
}
