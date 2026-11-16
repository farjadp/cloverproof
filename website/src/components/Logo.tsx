import Image from "next/image";
import horizontalOlive from "../../public/brand/cloverproof-horizontal-olive.webp";
import horizontalWhite from "../../public/brand/cloverproof-horizontal-white.webp";
import markOlive from "../../public/brand/cloverproof-mark-olive.webp";

/**
 * Official CloverProof logo (brand/logo/, supplied by Farjad Iranmehr).
 * Files are the originals with transparent padding trimmed — never redraw or recolour.
 */
export function Logo({ tone = "olive", className = "h-9 w-auto" }: { tone?: "olive" | "white"; className?: string }) {
  return (
    <Image
      src={tone === "white" ? horizontalWhite : horizontalOlive}
      alt="CloverProof"
      sizes="160px"
      priority={tone === "olive"}
      className={className}
    />
  );
}

/** Official mark for small decorative uses; hidden from assistive tech. */
export function CloverMark({ className = "h-7 w-auto" }: { className?: string }) {
  return <Image src={markOlive} alt="" aria-hidden="true" sizes="48px" className={className} />;
}
