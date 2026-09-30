interface AvatarProps {
  label: string
  size?: 'sm' | 'lg'
}

// Candidate ke initials wala gol avatar (hero me bada, messages me chhota)
export function Avatar({ label, size = 'sm' }: AvatarProps) {
  const sizing = size === 'lg' ? 'size-16 text-xl' : 'size-7 text-[11px]'
  return (
    <div
      aria-hidden="true"
      className={`${sizing} grid shrink-0 place-items-center rounded-full border border-border bg-gradient-to-br from-accent-soft to-surface-2 font-semibold tracking-wide text-fg select-none`}
    >
      {label}
    </div>
  )
}
