export function CloverMark({ className = "size-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 44" aria-hidden="true" className={className}>
      <g className="fill-olive">
        <circle cx="20" cy="10" r="9" />
        <circle cx="30" cy="20" r="9" />
        <circle cx="20" cy="30" r="9" />
        <circle cx="10" cy="20" r="9" />
      </g>
      <circle cx="20" cy="20" r="3.5" className="fill-ivory" />
      <path d="M20 33c1 7 6 9 10 10" className="fill-none stroke-olive" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <CloverMark />
      <span className="font-serif text-xl font-semibold tracking-tight text-ink">{name}</span>
    </span>
  );
}
