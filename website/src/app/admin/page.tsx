import type { Metadata } from "next";
import Link from "next/link";
import { purgeHealth } from "@/lib/admin/log";
import { isPasswordOnly } from "@/lib/admin/mfa-policy";
import { can } from "@/lib/admin/permissions";
import { adminDb, adminReady, csrfField, mfaOptional, requirePage } from "@/lib/admin/server";
import { AdminShell } from "./shell";
import { NotConfigured } from "./ui";

export const metadata: Metadata = { title: "Dashboard" };

export default async function AdminHome({ searchParams }: { searchParams: Promise<{ denied?: string }> }) {
  if (!adminReady()) return <NotConfigured />;
  const current = await requirePage("dashboard.view");
  const { denied } = await searchParams;
  const health = can(current.user.role, "log.view") ? await purgeHealth(adminDb()!, new Date()) : null;
  return (
    <AdminShell current={current} csrf={await csrfField()} active="/admin">
      <h1 className="font-serif text-3xl text-ink">Welcome, {current.user.display_name}</h1>
      <p className="mt-2 text-ink-soft">You are signed in as {current.user.role}. Sessions end after 30 minutes without activity.</p>
      {denied ? (
        <p role="alert" className="mt-6 rounded-md border border-rule bg-ivory px-4 py-3 text-sm text-ink">
          You don&apos;t have permission for that page.
        </p>
      ) : null}
      {isPasswordOnly(current, mfaOptional()) ? (
        <section aria-labelledby="mfa-title" className="mt-8 max-w-xl rounded-lg border border-rule bg-ivory p-5">
          <h2 id="mfa-title" className="font-serif text-xl text-ink">
            Two-step sign-in is off
          </h2>
          <p className="mt-2 text-sm text-ink-soft">
            Your account is protected by your password alone. Setting it up is recommended. Managing users and API keys and exporting the log are closed for every account while it is optional.
          </p>
          <Link href="/admin/mfa" className="mt-3 inline-flex min-h-11 items-center font-semibold text-olive underline underline-offset-4">
            Set up two-step sign-in
          </Link>
        </section>
      ) : null}
      {health ? (
        <section aria-labelledby="health-title" className="mt-8 max-w-xl rounded-lg border border-rule bg-ivory p-5">
          <h2 id="health-title" className="font-serif text-xl text-ink">
            Log retention
          </h2>
          <p className={`mt-2 text-sm ${health.stale ? "text-red-900" : "text-ink-soft"}`}>
            {health.last_ok_at
              ? `Last 60-day clean-up: ${new Date(health.last_ok_at).toISOString().slice(0, 16).replace("T", " ")} UTC.`
              : "The 60-day clean-up has not run yet (it runs within an hour of start-up, then daily)."}
            {health.stale && health.last_ok_at ? " Overdue — check the website service." : ""}
          </p>
        </section>
      ) : null}
    </AdminShell>
  );
}
