import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ChavePixCard } from "@/components/pagamentos/chave-pix.client";
import { MercadoPagoCard } from "@/components/pagamentos/mercadopago.client";
import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { recoveryAttemptCookieName } from "@/lib/bff/context.server";
import { currentOperationalContext } from "@/lib/bff/current-context.server";
import { readChavePix, readMercadoPagoConfig } from "@/lib/bff/mercadopago.server";
import {
  INITIAL_CHAVE_PIX_ACTION_STATE,
  INITIAL_MERCADOPAGO_ACTION_STATE,
  MERCADOPAGO_PERMISSION,
} from "@/lib/pagamentos/mercadopago-policy";

import { chavePixAction, mercadoPagoAction } from "./actions";

export const metadata: Metadata = {
  title: "Recebimento | TiaNet",
};

export default async function PagamentosRoute() {
  const cookieStore = await cookies();
  const dependencies = createRuntimeDependencies();
  const context = await currentOperationalContext();
  const [resultado, chave] = await Promise.all([
    readMercadoPagoConfig(cookieStore, context, dependencies),
    readChavePix(cookieStore, context, dependencies),
  ]);

  if (resultado.kind === "problem" && resultado.status === 401) {
    redirect(cookieStore.get(recoveryAttemptCookieName(dependencies.config)) ? "/login" : "/session/recover");
  }

  if (resultado.kind === "problem") {
    return (
      <section className="grid gap-3">
        <h1 className="text-xl font-semibold">Recebimento</h1>
        <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" role="alert">
          {resultado.message}
          <span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {resultado.correlationId}</span>
        </p>
      </section>
    );
  }

  return (
    <section className="grid gap-4">
      <h1 className="text-xl font-semibold">Recebimento</h1>
      {chave.kind === "ready" ? (
        <ChavePixCard
          action={chavePixAction}
          chave={chave.chave}
          initialState={INITIAL_CHAVE_PIX_ACTION_STATE}
          podeConfigurar={context.permissoes.includes(MERCADOPAGO_PERMISSION)}
        />
      ) : null}
      <MercadoPagoCard
        action={mercadoPagoAction}
        config={resultado.config}
        initialState={INITIAL_MERCADOPAGO_ACTION_STATE}
        podeConfigurar={context.permissoes.includes(MERCADOPAGO_PERMISSION)}
      />
    </section>
  );
}
