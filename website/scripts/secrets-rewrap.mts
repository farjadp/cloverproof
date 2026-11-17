// Master-key (KEK) rotation for website admin secrets: API keys and two-step sign-in secrets (ADR 0013; runbook §6). Order:
//   1. Railway: set the NEW key as WEBSITE_SECRETS_KEK + a NEW WEBSITE_SECRETS_KEK_ID, and the old
//      key and its id as WEBSITE_SECRETS_KEK_PREVIOUS + WEBSITE_SECRETS_KEK_PREVIOUS_ID. Redeploy.
//   2. In the website service shell: npm run secrets:rewrap
//   3. Only after it prints "Rotation complete": remove the _PREVIOUS variables and redeploy.
// It refuses to commit if anything would stay under the old key.
import pg from "pg";
import { kekRingFromEnv } from "../src/lib/admin/kek-env.ts";
import { rotateMasterKey } from "../src/lib/admin/rotation.ts";

async function main(): Promise<void> {
  const url = process.env.ADMIN_DATABASE_URL;
  if (!url) throw new Error("ADMIN_DATABASE_URL is not set");
  const keks = kekRingFromEnv();
  if (keks.length < 2) {
    throw new Error("Set WEBSITE_SECRETS_KEK_PREVIOUS and WEBSITE_SECRETS_KEK_PREVIOUS_ID (the old key) before rotating");
  }
  const client = new pg.Client({ connectionString: url });
  await client.connect();
  try {
    await client.query("begin");
    const n = await rotateMasterKey(client, { keks, hmacKey: Buffer.alloc(32), siteUrl: "" });
    await client.query("commit");
    console.log(`Rotation complete: re-sealed ${n.keys} API key(s) and ${n.mfa} two-step sign-in secret(s) under ${keks[0].id}; every value opens with it.`);
    console.log("You can now remove WEBSITE_SECRETS_KEK_PREVIOUS and WEBSITE_SECRETS_KEK_PREVIOUS_ID and redeploy.");
  } catch (error) {
    await client.query("rollback");
    console.error("Rolled back. Nothing changed. Keep WEBSITE_SECRETS_KEK_PREVIOUS.");
    throw error;
  } finally {
    await client.end();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : "failed");
  process.exit(1);
});
