import { NextResponse, type NextRequest } from "next/server";
import { defaultLocale, enabledLocales, type Locale } from "@/i18n/config";

const ADMIN_SESSION_COOKIE = "__Host-cp_admin";
const ADMIN_PRE_COOKIE = "__Host-cp_admin_pre";
const ADMIN_PUBLIC = ["/admin/login", "/admin/setup"];

function preferredLocale(request: NextRequest): Locale {
  const header = request.headers.get("accept-language") ?? "";
  const wanted = header
    .split(",")
    .map((part) => part.split(";")[0].trim().slice(0, 2).toLowerCase());
  return (wanted.find((l) => (enabledLocales as readonly string[]).includes(l)) as Locale) ?? defaultLocale;
}

function randomHex(bytes: number): string {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return Array.from(buf, (b) => b.toString(16).padStart(2, "0")).join("");
}

// /admin: strict CSP with a per-request nonce, no caching, no framing, not indexed (ADR 0012).
function admin(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const isPublic = ADMIN_PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  // Optimistic check only; every page and action verifies the session in the database.
  if (!isPublic && !request.cookies.get(ADMIN_SESSION_COOKIE)) {
    return NextResponse.redirect(new URL("/admin/login", request.url));
  }
  const nonce = btoa(randomHex(16));
  const dev = process.env.NODE_ENV === "development";
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'nonce-${nonce}'${dev ? " 'unsafe-inline'" : ""}`,
    "img-src 'self' data: blob:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    ...(dev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  // Pre-session CSRF token for the login / setup forms (double submit).
  let pre = request.cookies.get(ADMIN_PRE_COOKIE)?.value;
  const newPre = !pre || pre.length < 32;
  if (newPre) {
    pre = randomHex(32);
    const others = request.headers.get("cookie");
    requestHeaders.set("cookie", `${others ? `${others}; ` : ""}${ADMIN_PRE_COOKIE}=${pre}`);
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (!dev) response.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  if (newPre && pre) {
    response.cookies.set(ADMIN_PRE_COOKIE, pre, { httpOnly: true, secure: true, sameSite: "strict", path: "/" });
  }
  return response;
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return admin(request);
  const hasLocale = enabledLocales.some((l) => pathname === `/${l}` || pathname.startsWith(`/${l}/`));
  if (hasLocale) return;
  request.nextUrl.pathname = `/${preferredLocale(request)}${pathname === "/" ? "" : pathname}`;
  return NextResponse.redirect(request.nextUrl);
}

export const config = {
  matcher: ["/((?!_next|api|favicon.ico|.*\\..*).*)"],
};
