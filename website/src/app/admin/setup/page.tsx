import type { Metadata } from "next";
import { adminReady, preToken } from "@/lib/admin/server";
import { AuthCard, NotConfigured } from "../ui";
import { SetupForm } from "./SetupForm";

export const metadata: Metadata = { title: "Set your password" };

export default async function SetupPage() {
  if (!adminReady()) return <NotConfigured />;
  return (
    <AuthCard title="Set your password" intro="This link works once and expires. After this you'll set up two-step sign-in.">
      <SetupForm pre={await preToken()} />
    </AuthCard>
  );
}
