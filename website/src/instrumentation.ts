import type { Instrumentation } from "next";

// Website admin: 60-day system-log purge (ADR 0014) and error records for /admin requests.
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { startPurgeTimer } = await import("./lib/admin/background");
    startPurgeTimer();
  }
}

export const onRequestError: Instrumentation.onRequestError = async (error, request) => {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const path = request.path.split("?")[0];
  if (!path.startsWith("/admin")) return;
  const { logAdminError } = await import("./lib/admin/background");
  await logAdminError(path, error);
};
