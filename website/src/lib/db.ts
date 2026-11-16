import "server-only";
import { Pool } from "pg";

let pool: Pool | null = null;

/** Shared Postgres pool. Returns null when DATABASE_URL is not configured. */
export function getDb(): Pool | null {
  const url = process.env.DATABASE_URL;
  if (!url) return null;
  pool ??= new Pool({ connectionString: url, max: 5 });
  return pool;
}
