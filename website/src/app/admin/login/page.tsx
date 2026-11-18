import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { hasFullAccess } from "@/lib/admin/mfa-policy";
import { adminReady, currentSession, mfaOptional, preToken } from "@/lib/admin/server";
import { AuthCard, NotConfigured } from "../ui";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage() {
  if (!adminReady()) return <NotConfigured />;
  const current = await currentSession();
  if (current && hasFullAccess(current, mfaOptional())) redirect("/admin");
  return (
    <AuthCard title="Sign in" intro="Staff only. Accounts are created by an admin.">
      <LoginForm pre={await preToken()} />
    </AuthCard>
  );
}
