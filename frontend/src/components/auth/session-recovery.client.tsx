"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "../ui/button";

export function SessionRecovery() {
  const router = useRouter();
  const started = useRef(false);
  const [message, setMessage] = useState<string>();

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void (async () => {
      try {
        const response = await fetch("/api/auth/bootstrap", {
          cache: "no-store",
          headers: { "X-Correlation-ID": crypto.randomUUID(), "X-CSRF-Protection": "1" },
          method: "POST",
          redirect: "error",
        });
        if (response.ok) {
          router.replace("/app");
          router.refresh();
          return;
        }
        if (response.status === 401) {
          router.replace("/login");
          router.refresh();
          return;
        }
        const correlation = response.headers.get("X-Correlation-ID");
        const suffix = correlation ? ` Correlation ID: ${correlation}` : "";
        setMessage((response.status === 409
          ? "O contexto operacional ainda nao esta disponivel. Nenhuma carteira alternativa foi escolhida."
          : "Nao foi possivel restaurar a sessao agora.") + suffix);
      } catch {
        setMessage("Nao foi possivel restaurar a sessao agora.");
      }
    })();
  }, [router]);

  if (!message) return <p aria-live="polite" role="status">Restaurando sessao…</p>;
  return (
    <div className="grid gap-4" role="alert">
      <p>{message}</p>
      <Button onClick={() => router.replace("/login")} type="button">Voltar ao login</Button>
    </div>
  );
}
