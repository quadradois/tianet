"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type LoginRequest = Readonly<{
  email: string;
  segredo: string;
}>;

function publicMessage(status: number): string {
  if (status === 401) return "Nao foi possivel autenticar com os dados informados.";
  if (status >= 500) return "O servico esta temporariamente indisponivel.";
  return "Revise os campos e tente novamente.";
}

export function LoginForm() {
  const router = useRouter();
  const errorRef = useRef<HTMLParagraphElement>(null);
  const [message, setMessage] = useState<string>();
  const [pending, startTransition] = useTransition();

  useEffect(() => {
    if (message) errorRef.current?.focus();
  }, [message]);

  function submit(formData: FormData) {
    const body: LoginRequest = {
      email: String(formData.get("email") ?? ""),
      segredo: String(formData.get("segredo") ?? ""),
    };
    setMessage(undefined);
    startTransition(async () => {
      try {
        const response = await fetch("/api/auth/login", {
          body: JSON.stringify(body),
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            "X-Correlation-ID": crypto.randomUUID(),
            "X-CSRF-Protection": "1",
          },
          method: "POST",
          redirect: "error",
        });
        if (!response.ok) {
          setMessage(publicMessage(response.status));
          return;
        }
        router.replace("/app");
        router.refresh();
      } catch {
        setMessage("Nao foi possivel conectar ao servico.");
      }
    });
  }

  return (
    <form action={submit} className="grid gap-5" noValidate>
      <div className="grid gap-2">
        <Label htmlFor="email">E-mail</Label>
        <Input autoComplete="username" id="email" maxLength={254} minLength={3} name="email" required spellCheck={false} type="email" />
      </div>
      <div className="grid gap-2">
        <Label htmlFor="segredo">Senha</Label>
        <Input autoComplete="current-password" id="segredo" minLength={1} name="segredo" required type="password" />
      </div>
      {message ? <p aria-live="polite" className="text-sm text-destructive" ref={errorRef} role="alert" tabIndex={-1}>{message}</p> : null}
      <Button aria-disabled={pending} disabled={pending} type="submit">
        {pending ? "Entrando…" : "Entrar"}
      </Button>
    </form>
  );
}
