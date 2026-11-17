import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { adminReady, currentSession, preToken } from "@/lib/admin/server";
import { AuthCard, NotConfigured } from "../ui";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage() {
  if (!adminReady()) return <NotConfigured />;
  const current = await currentSession();
  if (current?.session.mfa_verified_at) redirect("/admin");
  return (
    <AuthCard title="Sign in" intro="Staff only. Accounts are created by an admin.">
      <LoginForm pre={await preToken()} />
    </AuthCard>
  );
}
