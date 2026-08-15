"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "../ui/button";

export function LogoutButton() {
  const router = useRouter();
  const [message, setMessage] = useState<string>();
  const [pending, startTransition] = useTransition();

  function logout() {
    setMessage(undefined);
    startTransition(async () => {
      try {
        await fetch("/api/auth/logout", {
          cache: "no-store",
          headers: { "X-Correlation-ID": crypto.randomUUID(), "X-CSRF-Protection": "1" },
          method: "POST",
          redirect: "error",
        });
        // O Route Handler sempre limpa o cookie local, mesmo quando o backend
        // remoto falha. Remova imediatamente a PII da tela em toda resposta.
        router.replace("/login");
        router.refresh();
      } catch {
        setMessage("Nao foi possivel encerrar a sessao. Tente novamente.");
      }
    });
  }

  return (
    <div className="grid justify-items-end gap-2">
      <Button disabled={pending} onClick={logout} size="compact" type="button" variant="outline">
        {pending ? "Saindo…" : "Sair"}
      </Button>
      {message ? <p aria-live="polite" className="max-w-60 text-right text-xs text-destructive" role="alert">{message}</p> : null}
    </div>
  );
}
