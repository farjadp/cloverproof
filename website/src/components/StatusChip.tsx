/** Small status label used on the roadmap and in "What's new". */
export function StatusChip({ children }: { children: React.ReactNode }) {
  return <span className="inline-block rounded bg-sage-soft px-2 py-0.5 text-xs font-semibold text-olive">{children}</span>;
}
