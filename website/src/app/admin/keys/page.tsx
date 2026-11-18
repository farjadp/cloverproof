import type { Metadata } from "next";
import { listKeys, PROVIDERS, type Provider } from "@/lib/admin/keys";
import { stepUpGate } from "@/lib/admin/mfa-policy";
import { adminDb, adminReady, csrfField, mfaOptional, requirePage } from "@/lib/admin/server";
import { AdminShell } from "../shell";
import { StepUpForm } from "../StepUpForm";
import { NotConfigured } from "../ui";
import { KeyCard } from "./KeyCard";

export const metadata: Metadata = { title: "API keys" };

const stamp = (d: Date | null) => (d ? new Date(d).toISOString().slice(0, 16).replace("T", " ") + " UTC" : null);

export default async function KeysPage() {
  if (!adminReady()) return <NotConfigured />;
  const current = await requirePage("keys.manage");
  const csrf = await csrfField();
  const gate = stepUpGate(current, mfaOptional());
  const keys = gate === "open" ? await listKeys(adminDb()!) : {};
  return (
    <AdminShell current={current} csrf={csrf} active="/admin/keys">
      <h1 className="font-serif text-3xl text-ink">API keys</h1>
      <p className="mt-1 mb-6 max-w-3xl text-ink-soft">
        Keys for the AI providers the future content agents will use. They are encrypted before they are stored, used only on the
        server, and never shown again after saving. No farmer or pilot data is ever sent to these providers. Every change is logged.
      </p>
      {gate !== "open" ? (
        <StepUpForm closed={gate === "closed"} csrf={csrf} path="/admin/keys" what="manage API keys" />
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2" aria-label="Providers">
          {(Object.keys(PROVIDERS) as Provider[]).map((p) => {
            const k = keys[p];
            return (
              <KeyCard
                key={p}
                csrf={csrf}
                info={{
                  provider: p,
                  label: PROVIDERS[p].label,
                  hint: PROVIDERS[p].hint,
                  active: k
                    ? {
                        last4: k.last4,
                        version: k.version,
                        created_at: stamp(k.created_at) ?? "",
                        created_by: k.created_by,
                        budget: k.monthly_budget_usd,
                        tested: stamp(k.last_test_at),
                        testOk: k.last_test_ok,
                      }
                    : null,
                }}
              />
            );
          })}
        </ul>
      )}
    </AdminShell>
  );
}
