import Image from "next/image";
import { localeMeta, type Locale } from "@/i18n/config";

/** Flag for a locale; decorative — the native language name is the accessible label. */
export function Flag({ locale, className = "h-4 w-auto" }: { locale: Locale; className?: string }) {
  return (
    <Image
      src={`/flags/${localeMeta[locale].flag}.svg`}
      alt=""
      aria-hidden="true"
      width={20}
      height={15}
      loading="lazy"
      className={`rounded-[2px] ring-1 ring-ink/15 ${className}`}
    />
  );
}
