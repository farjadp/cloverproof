// Create the first website admin (ADR 0012). Run in the Railway website service shell:
//   npm run admin:create -- --email you@example.com --name "Your Name" [--additional]
// Needs ADMIN_DATABASE_URL, WEBSITE_SECRETS_KEK, WEBSITE_ADMIN_HMAC_KEY (and SITE_URL for the link).
// Prints a one-time setup link (valid 72 h). Nothing secret is written to the log.
import { parseArgs } from "node:util";
import pg from "pg";
import { keyFromBase64 } from "../src/lib/admin/crypto.ts";
import { createFirstAdmin } from "../src/lib/admin/service.ts";

const { values } = parseArgs({
  options: { email: { type: "string" }, name: { type: "string" }, additional: { type: "boolean", default: false } },
});

async function main(): Promise<void> {
  if (!values.email || !values.name) throw new Error('usage: npm run admin:create -- --email you@example.com --name "Your Name"');
  const url = process.env.ADMIN_DATABASE_URL;
  if (!url) throw new Error("ADMIN_DATABASE_URL is not set");
  const config = {
    keks: [{ id: process.env.WEBSITE_SECRETS_KEK_ID || "k1", key: keyFromBase64("WEBSITE_SECRETS_KEK", process.env.WEBSITE_SECRETS_KEK) }],
    hmacKey: keyFromBase64("WEBSITE_ADMIN_HMAC_KEY", process.env.WEBSITE_ADMIN_HMAC_KEY),
    siteUrl:
      process.env.SITE_URL ??
      (process.env.RAILWAY_PUBLIC_DOMAIN ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}` : "http://localhost:3000"),
  };
  const client = new pg.Client({ connectionString: url });
  await client.connect();
  try {
    await client.query("begin");
    const { link } = await createFirstAdmin(client, config, { email: values.email, name: values.name, additional: values.additional }, new Date());
    await client.query("commit");
    console.log("Admin created. Open this link within 72 hours to set the password (it works once):");
    console.log(link);
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
