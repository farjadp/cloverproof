import type { Metadata } from "next";
import { redirect } from "next/navigation";
import QRCode from "qrcode";
import { isPasswordOnly } from "@/lib/admin/mfa-policy";
import { adminConfig, adminDb, csrfField, currentSession, mfaOptional } from "@/lib/admin/server";
import { pendingMfaSecret } from "@/lib/admin/service";
import { otpauthUri } from "@/lib/admin/totp";
import { AuthCard, NotConfigured } from "../ui";
import { MfaForm } from "./MfaForm";

export const metadata: Metadata = { title: "Two-step sign-in" };

export default async function MfaPage() {
  const db = adminDb();
  const config = adminConfig();
  if (!db || !config) return <NotConfigured />;
  const current = await currentSession();
  if (!current) redirect("/admin/login");
  const csrf = await csrfField();

  // One tree for both states, so the form keeps its result (recovery codes) when the page
  // re-renders after enrolment. Required for every account unless ADMIN_MFA_OPTIONAL is on (ADR 0012).
  const enrolling = !current.user.mfa_enabled_at;
  const optional = isPasswordOnly(current, mfaOptional());
  let enrol: React.ReactNode = null;
  if (enrolling) {
    const secret = await pendingMfaSecret(db, config, current);
    const svg = await QRCode.toString(otpauthUri(secret, current.user.email ?? current.user.display_name), {
      type: "svg",
      margin: 1,
      color: { dark: "#273125", light: "#ffffff" },
    });
    const grouped = secret.match(/.{1,4}/g)?.join(" ") ?? secret;
    enrol = (
      <>
        <div
          className="mx-auto mb-4 w-48 max-w-full rounded border border-rule bg-white p-2 [&>svg]:h-auto [&>svg]:w-full"
          role="img"
          aria-label="QR code for your authenticator app"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
        <details className="mb-6 text-sm text-ink-soft">
          <summary className="min-h-11 cursor-pointer py-2 text-olive">Can&apos;t scan? Enter the key by hand</summary>
          <p className="mt-2 break-all font-mono text-ink" aria-label="Setup key">
            {grouped}
          </p>
        </details>
      </>
    );
  }
  return (
    <AuthCard
      title={enrolling ? "Set up two-step sign-in" : current.session.mfa_verified_at ? "Two-step sign-in is on" : "Two-step sign-in"}
      intro={
        current.session.mfa_verified_at
          ? undefined
          : optional
          ? "Optional, and recommended. Scan the code with an authenticator app (1Password, Google Authenticator, Microsoft Authenticator…), then enter the 6-digit code it shows."
          : enrolling
          ? "Required for every admin account. Scan the code with an authenticator app (1Password, Google Authenticator, Microsoft Authenticator…), then enter the 6-digit code it shows."
          : "Enter the current code from your authenticator app."
      }
    >
      {enrol}
      <MfaForm key="mfa-form" csrf={csrf} enrolling={enrolling} optional={optional} />
    </AuthCard>
  );
}
