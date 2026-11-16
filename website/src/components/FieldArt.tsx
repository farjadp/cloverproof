// Abstract crop-row illustration in brand colours (no stock photography).
export function FieldArt() {
  const rows = Array.from({ length: 9 }, (_, i) => i);
  return (
    <svg viewBox="0 0 480 360" role="img" aria-label="Rows of a cultivated field under an open sky" className="h-auto w-full">
      <rect width="480" height="360" className="fill-sand" />
      <rect width="480" height="150" className="fill-sage-soft" />
      <circle cx="380" cy="70" r="26" className="fill-ivory" />
      <path d="M0 150 C 90 128, 170 140, 250 132 S 400 124, 480 138 L480 160 L0 160Z" className="fill-sage" />
      <path d="M0 160 L480 160 L480 360 L0 360Z" className="fill-olive" />
      {rows.map((i) => (
        <path
          key={i}
          d={`M${240 + (i - 4) * 14} 160 L${240 + (i - 4) * 110} 360`}
          className="stroke-olive-deep"
          strokeWidth={i % 2 ? 10 : 16}
          strokeLinecap="round"
        />
      ))}
      {rows.map((i) => (
        <path
          key={`l${i}`}
          d={`M${240 + (i - 4) * 14 + 5} 162 L${240 + (i - 4) * 110 + 30} 360`}
          className="stroke-sage"
          strokeWidth={3}
          strokeDasharray="2 9"
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
}
