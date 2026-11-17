import type { Metadata } from "next";
import { adminReady, csrfField, requirePage } from "@/lib/admin/server";
import { AdminShell } from "./shell";
import { NotConfigured } from "./ui";

export const metadata: Metadata = { title: "Dashboard" };

export default async function AdminHome({ searchParams }: { searchParams: Promise<{ denied?: string }> }) {
  if (!adminReady()) return <NotConfigured />;
  const current = await requirePage("dashboard.view");
  const { denied } = await searchParams;
  return (
    <AdminShell current={current} csrf={await csrfField()} active="/admin">
      <h1 className="font-serif text-3xl text-ink">Welcome, {current.user.display_name}</h1>
      <p className="mt-2 text-ink-soft">You are signed in as {current.user.role}. Sessions end after 30 minutes without activity.</p>
      {denied ? (
        <p role="alert" className="mt-6 rounded-md border border-rule bg-ivory px-4 py-3 text-sm text-ink">
          You don&apos;t have permission for that page.
        </p>
      ) : null}
    </AdminShell>
  );
}
