// Role matrix (ADR 0012). Checked in every server action and route handler.
export type WebsiteRole = "admin" | "editor" | "author";

export const ACTIONS = [
  "dashboard.view",
  "users.manage",
  "log.view",
  "log.export",
  "keys.manage",
  "posts.write_own",
  "posts.edit_any",
  "posts.publish",
  "media.upload",
  "media.manage",
] as const;
export type Action = (typeof ACTIONS)[number];

const MATRIX: Record<WebsiteRole, readonly Action[]> = {
  admin: ACTIONS,
  editor: ["dashboard.view", "posts.write_own", "posts.edit_any", "posts.publish", "media.upload", "media.manage"],
  author: ["dashboard.view", "posts.write_own", "media.upload"],
};

export function can(role: WebsiteRole, action: Action): boolean {
  return MATRIX[role].includes(action);
}

/** Actions that need a fresh MFA code (step-up) within STEP_UP_SECONDS. */
export const STEP_UP_ACTIONS: readonly Action[] = ["users.manage", "keys.manage", "log.export"];
export const STEP_UP_SECONDS = 5 * 60;

export function isWebsiteRole(value: unknown): value is WebsiteRole {
  return value === "admin" || value === "editor" || value === "author";
}
