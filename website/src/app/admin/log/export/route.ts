import { readLog, toCsv } from "@/lib/admin/log";
import { guardAction } from "@/lib/admin/server";
import { writeLog } from "@/lib/admin/service";

// POST only (CSRF token + fresh step-up); a GET export would be a CSRF-able data leak.
export async function POST(request: Request): Promise<Response> {
  const form = await request.formData();
  const guard = await guardAction("log.export", form, { stepUp: true });
  if (!guard.ok) {
    return new Response(guard.error === "STEP_UP" ? "Confirm with a new code first." : guard.error, { status: 403 });
  }
  const filter = Object.fromEntries(["kind", "outcome", "actor", "from", "to"].map((k) => [k, String(form.get(k) ?? "")]));
  const { rows } = await readLog(guard.db, filter, new Date(), 5000);
  await writeLog(guard.db, {
    actor: guard.current.user.id,
    kind: "admin",
    action: "log.export",
    outcome: "ok",
    meta: guard.meta,
    detail: { count: rows.length },
  });
  const name = `cloverproof-admin-log-${new Date().toISOString().slice(0, 10)}.csv`;
  return new Response(toCsv(rows), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${name}"`,
      "Cache-Control": "no-store",
    },
  });
}
