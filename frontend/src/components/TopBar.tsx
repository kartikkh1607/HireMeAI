import { Globe, SquarePen } from 'lucide-react'
import type { ComponentType } from 'react'
import type { LinkKind, ProfileLink } from '../lib/profile'
import { GitHubIcon, LeetCodeIcon, LinkedInIcon } from './BrandIcons'

const ICONS: Record<LinkKind, ComponentType<{ size?: number }>> = {
  linkedin: LinkedInIcon,
  github: GitHubIcon,
  leetcode: LeetCodeIcon,
  portfolio: Globe,
}

interface TopBarProps {
  name: string | null
  links: ProfileLink[]
  canReset: boolean
  onNewChat: () => void
}

export function TopBar({ name, links, canReset, onNewChat }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 border-b border-border/60 bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-3 sm:px-5">
        <div className="flex min-w-0 flex-1 items-center gap-2.5">
          <Logo />
          <span className="text-[15px] font-semibold tracking-tight">HireMeAI</span>
          {name && (
            // Mobile pe jagah kam hai - naam hero me dikh hi jaata hai
            <span className="hidden min-w-0 items-center gap-2.5 text-sm text-muted sm:flex">
              <span aria-hidden="true" className="h-4 w-px bg-border" />
              <span className="truncate">{name}</span>
            </span>
          )}
        </div>

        {links.length > 0 && (
          <nav aria-label="Candidate profiles" className="flex items-center gap-0.5">
            {links.map(({ kind, label, url }) => {
              const Icon = ICONS[kind]
              return (
                <a
                  key={kind}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${label} (opens in new tab)`}
                  title={label}
                  className="grid size-9 place-items-center rounded-lg text-muted transition-colors hover:bg-surface-2 hover:text-fg"
                >
                  <Icon size={17} />
                </a>
              )
            })}
          </nav>
        )}

        <button
          type="button"
          onClick={onNewChat}
          disabled={!canReset}
          aria-label="New chat"
          title="New chat"
          className="ml-1 inline-flex h-9 items-center gap-2 rounded-lg border border-border px-2.5 text-sm font-medium text-fg transition-colors hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent sm:px-3"
        >
          <SquarePen size={16} aria-hidden="true" />
          <span className="hidden sm:inline">New chat</span>
        </button>
      </div>
    </header>
  )
}

function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true" className="shrink-0">
      <rect width="32" height="32" rx="9" fill="var(--accent)" />
      <path d="M11 9.5v13M21 9.5v13M11 16h10" stroke="var(--bg)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}
