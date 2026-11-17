import Link from "next/link";
import { can, type Action } from "@/lib/admin/permissions";
import type { Current } from "@/lib/admin/service";
import { logoutAction } from "./actions";

const NAV: { href: string; label: string; action: Action }[] = [
  { href: "/admin", label: "Dashboard", action: "dashboard.view" },
];

/** Signed-in frame: header with navigation by role, and sign-out (POST + CSRF). */
export function AdminShell({
  current,
  csrf,
  active,
  children,
}: {
  current: Current;
  csrf: string;
  active: string;
  children: React.ReactNode;
}) {
  const items = NAV.filter((n) => can(current.user.role, n.action));
  return (
    <div className="min-h-dvh">
      <header className="border-b border-rule bg-ivory">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/admin" className="font-serif text-lg text-olive">
            CloverProof <span className="text-ink-soft">admin</span>
          </Link>
          <nav aria-label="Admin" className="order-3 w-full overflow-x-auto sm:order-none sm:w-auto">
            <ul className="flex gap-1">
              {items.map((n) => (
                <li key={n.href}>
                  <Link
                    href={n.href}
                    aria-current={active === n.href ? "page" : undefined}
                    className="inline-flex min-h-11 items-center rounded-md px-3 text-sm text-ink hover:bg-sand aria-[current=page]:bg-sage-soft aria-[current=page]:font-semibold"
                  >
                    {n.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <div className="ms-auto flex items-center gap-3 text-sm">
            <span className="hidden text-ink-soft sm:inline">
              {current.user.display_name} · {current.user.role}
            </span>
            <form action={logoutAction}>
              <input type="hidden" name="csrf" value={csrf} />
              <button type="submit" className="min-h-11 rounded-md px-3 text-olive underline underline-offset-4">
                Sign out
              </button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}
