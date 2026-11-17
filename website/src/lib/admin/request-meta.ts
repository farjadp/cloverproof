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

const HEADER_NAME = /^[a-z0-9-]{1,64}$/;

/**
 * Client address from the ONE header the operator trusts (env TRUSTED_PROXY_HEADER; A-S2).
 * Empty by default: then there is no client IP, the per-IP sign-in limit is off and the log
 * stores no IP prefix. Set it only after a staging probe shows the proxy overwrites a
 * client-sent value (runbook §5). For X-Forwarded-For only the LAST entry is used (the one
 * the proxy appended); any other header must hold exactly one IP address.
 */
export function clientIp(trustedHeader: string | null | undefined, get: (name: string) => string | null): string | null {
  const name = trustedHeader?.trim().toLowerCase();
  if (!name || !HEADER_NAME.test(name)) return null;
  const raw = get(name);
  if (!raw) return null;
  const value = name === "x-forwarded-for" ? (raw.split(",").at(-1) ?? "").trim() : raw.trim();
  return isIP(value) ? value : null;
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
