// Operator recovery for a website admin account (ADR 0012). Run in the website service shell:
//   npm run admin:reset -- --email user@example.com [--mfa]
// Issues a one-time password-reset link (1 h). With --mfa also clears two-step sign-in and
// recovery codes so the user enrols again. Always ends all of the user's sessions. Logged.
import { parseArgs } from "node:util";
import pg from "pg";
import { keyFromBase64 } from "../src/lib/admin/crypto.ts";
import { issueLink, linkUrl, normaliseEmail, revokeAllSessions, writeLog } from "../src/lib/admin/service.ts";

const { values } = parseArgs({ options: { email: { type: "string" }, mfa: { type: "boolean", default: false } } });

async function main(): Promise<void> {
  if (!values.email) throw new Error("usage: npm run admin:reset -- --email user@example.com [--mfa]");
  const url = process.env.ADMIN_DATABASE_URL;
  if (!url) throw new Error("ADMIN_DATABASE_URL is not set");
  keyFromBase64("WEBSITE_ADMIN_HMAC_KEY", process.env.WEBSITE_ADMIN_HMAC_KEY);
  const siteUrl =
    process.env.SITE_URL ?? (process.env.RAILWAY_PUBLIC_DOMAIN ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}` : "http://localhost:3000");
  const client = new pg.Client({ connectionString: url });
  await client.connect();
  try {
    await client.query("begin");
    const { rows } = await client.query<{ id: string }>(
      "select id from website_user where email = $1 and deleted_at is null and disabled_at is null",
      [normaliseEmail(values.email)],
    );
    if (!rows[0]) throw new Error("no active user with that e-mail");
    const id = rows[0].id;
    const now = new Date();
    if (values.mfa) {
      await client.query("update website_user set mfa_secret_enc = null, mfa_enabled_at = null where id = $1", [id]);
      await client.query("delete from website_user_recovery_code where user_id = $1", [id]);
    }
    await client.query("update website_user set failed_logins = 0, locked_until = null where id = $1", [id]);
    await revokeAllSessions(client, id, now);
    const token = await issueLink(client, id, "password_reset", null, now);
    await writeLog(client, { kind: "admin", action: values.mfa ? "user.reset_mfa" : "user.reset_link", outcome: "ok", targetType: "website_user", targetId: id, detail: { via: "cli" } });
    await client.query("commit");
    console.log(`Sessions ended${values.mfa ? ", two-step sign-in cleared" : ""}. One-time link (1 hour):`);
    console.log(linkUrl({ keks: [], hmacKey: Buffer.alloc(0), siteUrl }, token));
  } catch (error) {
    await client.query("rollback");
    throw error;
  } finally {
    await client.end();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : "failed");
  process.exit(1);
});
