import { BadgeCheck, FolderGit2, Trophy, Wrench, type LucideIcon } from 'lucide-react'
import { firstName, initials } from '../lib/profile'
import { Avatar } from './Avatar'

interface Suggestion {
  icon: LucideIcon
  title: string
  subtitle: string
  question: string
}

function suggestionsFor(first: string): Suggestion[] {
  return [
    {
      icon: FolderGit2,
      title: 'Projects',
      subtitle: 'What was built and the tech behind it',
      question: `Walk me through ${first}'s projects and the tech stack used in each.`,
    },
    {
      icon: Wrench,
      title: 'Skills',
      subtitle: 'Languages, frameworks and tools',
      question: `What are ${first}'s key technical skills?`,
    },
    {
      icon: Trophy,
      title: 'Achievements & hackathons',
      subtitle: 'Competitions, coding streaks and wins',
      question: `What achievements and hackathons has ${first} been part of?`,
    },
    {
      icon: BadgeCheck,
      title: 'Certifications',
      subtitle: 'Cloud and professional credentials',
      question: `What certifications does ${first} hold?`,
    },
  ]
}

interface EmptyStateProps {
  name: string | null
  onPick: (question: string) => void
}

export function EmptyState({ name, onPick }: EmptyStateProps) {
  const first = firstName(name)

  return (
    <div className="fade-in mx-auto flex w-full max-w-[760px] flex-1 flex-col justify-center px-4 py-10 sm:px-6">
      <div className="mb-8 flex flex-col items-center text-center sm:mb-10">
        <Avatar label={initials(name)} size="lg" />
        <h1 className="mt-5 text-2xl font-semibold tracking-tight text-balance sm:text-[28px]">
          Ask me anything about {name ?? 'the candidate'}
        </h1>
        <p className="mt-2 max-w-md text-[15px] text-pretty text-muted">
          An AI assistant for recruiters that answers only from the resume.
        </p>
      </div>

      <ul className="grid grid-cols-2 gap-2.5 sm:gap-3" aria-label="Suggested questions">
        {suggestionsFor(first).map(({ icon: Icon, title, subtitle, question }) => (
          <li key={title} className="flex">
            <button
              type="button"
              onClick={() => onPick(question)}
              className="group flex w-full flex-col items-start gap-2 rounded-2xl border border-border bg-surface/40 p-3 text-left transition-colors hover:border-subtle/50 hover:bg-surface sm:p-4"
            >
              <Icon size={18} aria-hidden="true" className="text-subtle transition-colors group-hover:text-accent" />
              <span>
                <span className="block text-sm leading-snug font-medium">{title}</span>
                <span className="mt-0.5 block text-[13px] leading-snug text-muted">{subtitle}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
