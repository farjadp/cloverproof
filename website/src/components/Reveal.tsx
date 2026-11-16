"use client";

import type { ReactNode } from "react";
import { useInView } from "./useInView";

/** Fades and lifts its children in when scrolled into view. */
export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: 0 | 1 | 2 | 3 | 4; className?: string }) {
  const { ref, inView } = useInView<HTMLDivElement>(0.15);
  const delays = ["delay-0", "delay-100", "delay-200", "delay-300", "delay-500"];
  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ease-out ${delays[delay]} ${inView ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0"} ${className}`}
    >
      {children}
    </div>
  );
}
