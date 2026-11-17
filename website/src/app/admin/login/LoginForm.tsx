"use client";

import { useActionState } from "react";
import { loginAction, type LoginState } from "./actions";
import { Field, FormError, Submit } from "../ui";

export function LoginForm({ pre }: { pre: string }) {
  const [state, action, pending] = useActionState<LoginState, FormData>(loginAction, { error: null });
  return (
    <form action={action} noValidate={false}>
      <input type="hidden" name="pre" value={pre} />
      <FormError message={state.error} />
      <Field label="E-mail" name="email" type="email" autoComplete="username" inputMode="email" maxLength={320} />
      <Field label="Password" name="password" type="password" autoComplete="current-password" maxLength={128} />
      <Submit pending={pending}>{pending ? "Signing in…" : "Sign in"}</Submit>
    </form>
  );
}
