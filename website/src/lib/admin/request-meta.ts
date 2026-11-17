import { isIP } from "node:net";

// Only a network prefix is ever stored (IPv4 /24, IPv6 /48) — never a full address (ADR 0014).

function expandIpv6(ip: string): number[] | null {
  const [head, tail] = ip.split("::");
  if (ip.split("::").length > 2) return null;
  const part = (s: string) => (s ? s.split(":") : []);
  const h = part(head);
  const t = tail === undefined ? [] : part(tail);
  const missing = 8 - h.length - t.length;
  if (missing < 0 || (tail === undefined && missing !== 0)) return null;
  const groups = [...h, ...Array(missing).fill("0"), ...t].map((g) => parseInt(g, 16));
  return groups.length === 8 && groups.every((g) => g >= 0 && g <= 0xffff) ? groups : null;
}

export function ipPrefix(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let ip = raw.trim();
  if (ip.startsWith("::ffff:") && isIP(ip.slice(7)) === 4) ip = ip.slice(7);
  if (isIP(ip) === 4) {
    const [a, b, c] = ip.split(".");
    return `${a}.${b}.${c}.0/24`;
  }
  if (isIP(ip) === 6) {
    const groups = expandIpv6(ip.split("%")[0]);
    if (!groups) return null;
    return `${groups.slice(0, 3).map((g) => g.toString(16)).join(":")}::/48`;
  }
  return null;
}

/**
 * Client address as seen by Railway's edge: X-Real-IP first (the header Railway documents),
 * else the LAST X-Forwarded-For entry (the one the edge appended). The first XFF entry is
 * client-controlled and never used. Verify on staging with a spoofed header before relying on it.
 */
export function clientIp(forwardedFor: string | null, realIp: string | null): string | null {
  const real = realIp?.trim();
  if (real) return real;
  const parts = forwardedFor?.split(",").map((x) => x.trim()).filter(Boolean) ?? [];
  return parts.at(-1) ?? null;
}

/** Browser family only (no version, OS or device). */
export function uaFamily(ua: string | null | undefined): string | null {
  if (!ua) return null;
  if (/Edg\//.test(ua)) return "Edge";
  if (/OPR\//.test(ua)) return "Opera";
  if (/Firefox\//.test(ua)) return "Firefox";
  if (/Chrome\//.test(ua) || /CriOS\//.test(ua)) return "Chrome";
  if (/Safari\//.test(ua)) return "Safari";
  if (/curl|wget|python|node|go-http/i.test(ua)) return "Script";
  return "Other";
}
