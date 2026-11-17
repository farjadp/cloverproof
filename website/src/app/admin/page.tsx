import type { Metadata } from "next";
import { purgeHealth } from "@/lib/admin/log";
import { can } from "@/lib/admin/permissions";
import { adminDb, adminReady, csrfField, requirePage } from "@/lib/admin/server";
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
