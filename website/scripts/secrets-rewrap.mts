// Master-key (KEK) rotation for website admin API keys (ADR 0013). In the website service shell:
//   1. Set the new key as WEBSITE_SECRETS_KEK (+ _ID) and the old one as WEBSITE_SECRETS_KEK_PREVIOUS (+ _ID).
//   2. npm run secrets:rewrap
//   3. Remove WEBSITE_SECRETS_KEK_PREVIOUS once it reports success.
import pg from "pg";
import { keyFromBase64 } from "../src/lib/admin/crypto.ts";
import { rewrapAll } from "../src/lib/admin/keys.ts";

async function main(): Promise<void> {
  const url = process.env.ADMIN_DATABASE_URL;
  if (!url) throw new Error("ADMIN_DATABASE_URL is not set");
  const keks = [{ id: process.env.WEBSITE_SECRETS_KEK_ID || "k1", key: keyFromBase64("WEBSITE_SECRETS_KEK", process.env.WEBSITE_SECRETS_KEK) }];
  if (process.env.WEBSITE_SECRETS_KEK_PREVIOUS) {
    keks.push({ id: process.env.WEBSITE_SECRETS_KEK_PREVIOUS_ID || "previous", key: keyFromBase64("WEBSITE_SECRETS_KEK_PREVIOUS", process.env.WEBSITE_SECRETS_KEK_PREVIOUS) });
  }
  const client = new pg.Client({ connectionString: url });
  await client.connect();
  try {
    await client.query("begin");
    const n = await rewrapAll(client, { keks, hmacKey: Buffer.alloc(32), siteUrl: "" });
    await client.query("commit");
    console.log(`Re-sealed ${n} active key(s) under ${keks[0].id}.`);
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
