"use client";

import { useRouter } from "next/navigation";
import { startTransition, useActionState, useEffect, useState } from "react";

import type { OpenAIActionState, OpenAIConnection, OpenAIDiagnostic, OpenAIState } from "../../lib/openai/openai-policy";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";

type Action = (state: OpenAIActionState, formData: FormData) => Promise<OpenAIActionState>;
type Props = Readonly<{ action: Action; connection: OpenAIConnection; initialState: OpenAIActionState; podeGerir: boolean }>;

const POLLING_MS = 3_000;
const MAX_POLLING_MS = 10 * 60_000;
const DIAGNOSTIC_WINDOW_MS = 60_000;

const LABELS: Record<OpenAIState, string> = {
  DESABILITADO: "Desabilitado", INDISPONIVEL: "Indisponível", DESCONECTADO: "Desconectado",
  AGUARDANDO_USUARIO: "Aguardando você", CONECTADO: "Conectado", LIMITE_ATINGIDO: "Limite atingido",
  ERRO: "Erro", ERRO_RESULTADO_DESCONHECIDO: "Resultado desconhecido",
};

const DESCRIPTIONS: Record<OpenAIState, string> = {
  DESABILITADO: "O recurso está desligado na configuração deste ambiente.",
  INDISPONIVEL: "O processo local do Codex não está disponível.",
  DESCONECTADO: "Nenhuma conta OpenAI está conectada neste ambiente.",
  AGUARDANDO_USUARIO: "Conclua o login no endereço oficial da OpenAI.",
  CONECTADO: "A conta está pronta para o piloto administrativo.",
  LIMITE_ATINGIDO: "A conta está conectada, mas uma janela de uso chegou ao limite.",
  ERRO: "A última operação não pôde ser concluída.",
  ERRO_RESULTADO_DESCONHECIDO: "A operação terminou sem confirmação segura do resultado.",
};

function dispatch(action: (data: FormData) => void, intent: string) {
  const data = new FormData();
  data.set("intent", intent);
  startTransition(() => action(data));
}

function useConnectionPolling(active: boolean, expiresAt?: string) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const supplied = expiresAt ? Date.parse(expiresAt) : Number.NaN;
    const fallbackDeadline = Date.now() + MAX_POLLING_MS;
    const deadline = Number.isFinite(supplied) ? Math.min(supplied, fallbackDeadline) : fallbackDeadline;
    if (Date.now() >= deadline) return;
    let lastRefreshAt = Number.NEGATIVE_INFINITY;
    const stop = () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
    const refreshWhenVisible = () => {
      const now = Date.now();
      if (now >= deadline) { stop(); return; }
      if (document.visibilityState !== "visible" || now - lastRefreshAt < 250) return;
      lastRefreshAt = now;
      router.refresh();
    };
    const timer = window.setInterval(() => {
      refreshWhenVisible();
    }, POLLING_MS);
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return stop;
  }, [active, expiresAt, router]);
}

function Notice({ state }: Readonly<{ state: OpenAIActionState }>) {
  if (state.kind === "idle") return null;
  const problem = state.kind === "problem";
  return <p className={problem ? "rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm" : "rounded-md border border-border bg-muted/40 p-3 text-sm"} role={problem ? "alert" : "status"}>{state.message}<span className="mt-1 block text-xs text-muted-foreground">Correlation ID: {state.correlationId}</span></p>;
}

function Challenge({ challenge }: Readonly<{ challenge: Extract<OpenAIActionState, { kind: "login" }>["challenge"] }>) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(challenge.userCode);
    setCopied(true);
  }
  return <div className="grid gap-3 rounded-xl border border-border bg-card p-5" aria-labelledby="openai-login-title">
    <h2 className="font-semibold" id="openai-login-title">Concluir login na OpenAI</h2>
    <p className="text-sm text-muted-foreground">Abra somente o endereço oficial abaixo e informe este código temporário. Ele expira em <time dateTime={challenge.expiresAt}>{new Date(challenge.expiresAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</time>.</p>
    <div className="flex flex-wrap items-center gap-2"><code className="rounded-md border border-border bg-muted px-3 py-2 text-lg font-semibold tracking-wider">{challenge.userCode}</code><Button onClick={() => void copy()} type="button" variant="outline">{copied ? "Código copiado" : "Copiar código"}</Button></div>
    <a className="inline-flex min-h-10 w-fit items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" href={challenge.verificationUrl} rel="noopener noreferrer" target="_blank">Abrir login oficial da OpenAI</a>
  </div>;
}

function formatReset(timestamp: number | null): string {
  if (timestamp === null) return "Renovação não informada";
  return `Renova em ${new Date(timestamp * 1_000).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}`;
}

function formatDuration(minutes: number | null): string {
  if (minutes === null) return "Período não informado";
  if (minutes % 1_440 === 0) return `${minutes / 1_440} ${minutes === 1_440 ? "dia" : "dias"}`;
  if (minutes % 60 === 0) return `${minutes / 60} ${minutes === 60 ? "hora" : "horas"}`;
  return `${minutes} minutos`;
}

type UsageData = Pick<OpenAIDiagnostic, "observedAt" | "rateLimitsStatus" | "rateLimits">;

function windowTone(usedPercent: number): string {
  if (usedPercent >= 90) return "bg-destructive";
  if (usedPercent >= 70) return "bg-warning";
  return "bg-success";
}

function usageName(limitId: string | null, index: number): string {
  if (limitId === "codex") return "Uso geral do Codex";
  if (limitId?.startsWith("codex_")) return "Uso adicional do Codex";
  return `Janela de uso ${index + 1}`;
}

function UsageWindow({ label, value }: Readonly<{
  label: string;
  value: OpenAIDiagnostic["rateLimits"][number]["primary"];
}>) {
  if (!value) return null;
  const remaining = 100 - value.usedPercent;
  return (
    <div className="grid gap-2 rounded-lg border border-border bg-background p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold">{label}</p>
          <p className="text-xs text-muted-foreground">{formatDuration(value.windowDurationMinutes)}</p>
        </div>
        <p className="text-right text-sm font-semibold">{remaining}% disponível</p>
      </div>
      <div
        aria-label={`${value.usedPercent}% usado; ${remaining}% disponível`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={value.usedPercent}
        className="h-2 overflow-hidden rounded-full bg-muted"
        role="progressbar"
      >
        <span className={cn("block h-full rounded-full", windowTone(value.usedPercent))} style={{ width: `${value.usedPercent}%` }} />
      </div>
      <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
        <span>{value.usedPercent}% usado</span>
        <span>{formatReset(value.resetsAt)}</span>
      </div>
    </div>
  );
}

function UsageOverview({ usage }: Readonly<{ usage: UsageData | null }>) {
  return (
    <section className="rounded-xl border border-border bg-card shadow-sm" aria-labelledby="limites-title">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
        <div>
          <h2 className="font-semibold" id="limites-title">Limites de uso</h2>
          <p className="mt-1 text-sm text-muted-foreground">Consumo informado pela OpenAI na última consulta.</p>
        </div>
        {usage ? <p className="text-xs text-muted-foreground">Atualizado em <time dateTime={usage.observedAt}>{new Date(usage.observedAt).toLocaleString("pt-BR")}</time></p> : null}
      </div>
      <div className="grid gap-4 p-5">
        {!usage ? <div className="rounded-lg bg-muted/60 p-4"><p className="text-sm font-medium">Limites ainda não consultados</p><p className="mt-1 text-sm text-muted-foreground">Use “Atualizar diagnóstico” para buscar os dados atuais.</p></div> : null}
        {usage?.rateLimitsStatus === "error" ? <p className="rounded-lg border border-warning/40 bg-warning-subtle p-4 text-sm">A OpenAI não informou os limites nesta consulta.</p> : null}
        {usage?.rateLimitsStatus === "ok" && usage.rateLimits.length === 0 ? <p className="text-sm text-muted-foreground">Nenhuma janela de uso foi informada.</p> : null}
        {usage?.rateLimitsStatus === "ok" ? usage.rateLimits.map((limit, index) => (
          <div className="grid gap-3" key={limit.limitId ?? `limite-${index}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold">{usageName(limit.limitId, index)}</h3>
              {limit.planType ? <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium">Plano {limit.planType}</span> : null}
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              <UsageWindow label="Janela principal" value={limit.primary} />
              <UsageWindow label="Janela ampliada" value={limit.secondary} />
            </div>
          </div>
        )) : null}
      </div>
    </section>
  );
}

function ModelsOverview({ diagnostic }: Readonly<{ diagnostic: OpenAIDiagnostic | null }>) {
  return (
    <section className="rounded-xl border border-border bg-card shadow-sm" aria-labelledby="modelos-title">
      <div className="border-b border-border px-5 py-4">
        <h2 className="font-semibold" id="modelos-title">Modelos disponíveis</h2>
        <p className="mt-1 text-sm text-muted-foreground">Catálogo observado no diagnóstico atual.</p>
      </div>
      <div className="p-5">
        {!diagnostic ? <p className="text-sm text-muted-foreground">Atualize o diagnóstico para consultar os modelos liberados nesta conta.</p> : null}
        {diagnostic?.modelsStatus === "error" ? <p className="text-sm text-muted-foreground">Consulta de modelos indisponível.</p> : null}
        {diagnostic?.modelsStatus === "ok" && diagnostic.models.length === 0 ? <p className="text-sm text-muted-foreground">Nenhum modelo informado.</p> : null}
        {diagnostic?.modelsStatus === "ok" && diagnostic.models.length ? (
          <ul className="grid gap-2">
            {diagnostic.models.map((model) => (
              <li className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm" key={model.id}>
                <span>{model.displayName}{model.default ? " (padrão)" : ""}</span>
                {model.default ? <span className="rounded-full bg-success-subtle px-2 py-1 text-xs font-semibold text-success-foreground-strong">Padrão</span> : null}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

export function OpenAIScreen({ action, connection, initialState, podeGerir }: Props) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const [diagnosticBlocked, setDiagnosticBlocked] = useState(false);
  const [expiredChallenge, setExpiredChallenge] = useState<string | null>(null);
  const challenge = "challenge" in state ? state.challenge : undefined;
  const waiting = connection.state === "AGUARDANDO_USUARIO";
  const loginPending = waiting || (state.kind === "login" && !connection.accountConnected);
  const diagnostic = state.kind === "diagnostic"
    && connection.usageSummary?.observedAt === state.diagnostic.observedAt
    ? state.diagnostic
    : null;
  const usage: UsageData | null = diagnostic ?? connection.usageSummary;
  const highestUsage = usage?.rateLimitsStatus === "ok"
    ? Math.max(-1, ...usage.rateLimits.flatMap((limit) => [limit.primary, limit.secondary].flatMap((item) => item ? [item.usedPercent] : [])))
    : -1;
  useConnectionPolling(loginPending, challenge?.expiresAt);
  const router = useRouter();
  useEffect(() => {
    if (!challenge || !loginPending) return;
    const remaining = Math.min(MAX_POLLING_MS, Math.max(0, Date.parse(challenge.expiresAt) - Date.now()));
    const timer = window.setTimeout(() => {
      setExpiredChallenge(`${challenge.userCode}\0${challenge.expiresAt}`);
      router.refresh();
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [challenge, loginPending, router]);
  useEffect(() => {
    if (!diagnosticBlocked) return;
    const timer = window.setTimeout(() => setDiagnosticBlocked(false), DIAGNOSTIC_WINDOW_MS);
    return () => window.clearTimeout(timer);
  }, [diagnosticBlocked]);

  function run(intent: "conectar" | "desconectar" | "diagnostico") {
    if (intent === "diagnostico") setDiagnosticBlocked(true);
    dispatch(formAction, intent);
  }

  return <section className="grid max-w-5xl gap-5">
    <div className="grid gap-1">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Integração inteligente</p>
      <h1 className="text-2xl font-semibold tracking-tight">Conexão OpenAI</h1>
      <p className="max-w-2xl text-sm leading-6 text-muted-foreground">Acompanhe a conexão usada pelo Codex, o consumo informado e os modelos disponíveis neste ambiente.</p>
    </div>

    <section className="overflow-hidden rounded-xl border border-border bg-card shadow-sm" aria-labelledby="conexao-title">
      <div className={cn("h-1", connection.state === "CONECTADO" ? "bg-success" : connection.state === "AGUARDANDO_USUARIO" ? "bg-warning" : "bg-destructive")} />
      <div className="grid gap-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="grid gap-2">
            <p className="flex w-fit items-center gap-2 rounded-full bg-muted px-3 py-1 text-sm font-semibold">
              <span aria-hidden="true" className={cn("size-2.5 rounded-full", connection.state === "CONECTADO" ? "bg-success" : connection.state === "AGUARDANDO_USUARIO" ? "bg-warning" : "bg-destructive")} />
              {LABELS[connection.state]}
            </p>
            <div>
              <h2 className="text-lg font-semibold" id="conexao-title">Conta e capacidade</h2>
              <p className="mt-1 text-sm text-muted-foreground">{DESCRIPTIONS[connection.state]}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button disabled={pending || diagnosticBlocked || !connection.enabled || !connection.processAvailable} onClick={() => run("diagnostico")} type="button">
              {pending ? "Consultando..." : diagnosticBlocked ? "Diagnóstico disponível em até 60s" : "Atualizar diagnóstico"}
            </Button>
            {podeGerir && connection.state !== "CONECTADO" && connection.state !== "DESABILITADO" && connection.state !== "INDISPONIVEL" ? <Button disabled={pending || waiting} onClick={() => run("conectar")} type="button" variant="outline">{pending ? "Iniciando..." : waiting ? "Aguardando login..." : "Conectar conta OpenAI"}</Button> : null}
            {loginPending ? <Button disabled={pending} onClick={() => router.refresh()} type="button" variant="outline">Verificar agora</Button> : null}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border bg-background p-4"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Conexão</p><p className="mt-2 font-semibold">{connection.accountConnected ? "Ativa neste ambiente" : "Não ativa"}</p></div>
          <div className="rounded-lg border border-border bg-background p-4"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Plano informado</p><p className="mt-2 font-semibold">{connection.planType ?? "Não informado"}</p></div>
          <div className="rounded-lg border border-border bg-background p-4"><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Maior consumo</p><p className="mt-2 font-semibold">{highestUsage >= 0 ? `${highestUsage}% consumido` : "Aguardando consulta"}</p></div>
        </div>

        {connection.accountConnected ? <p className="rounded-lg border border-success/30 bg-success-subtle p-3 text-sm text-success-foreground-strong" role="status">Login confirmado. A conta OpenAI está conectada a este ambiente.</p> : null}
        <Notice state={state} />
        {!podeGerir ? <p className="text-sm text-muted-foreground">Seu acesso permite consultar a conexão, mas não conectar ou desconectar contas.</p> : null}
        {podeGerir && (connection.accountConnected || loginPending) ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <p className="max-w-2xl text-xs leading-5 text-muted-foreground">A desconexão remove a sessão deste ambiente. A interface não confirma revogação remota na sua conta OpenAI.</p>
            <Button className="border-destructive/40 text-destructive-foreground-strong hover:bg-destructive-subtle" disabled={pending} onClick={() => run("desconectar")} type="button" variant="outline">{pending ? "Desconectando..." : loginPending ? "Cancelar tentativa" : "Desconectar deste ambiente"}</Button>
          </div>
        ) : null}
      </div>
    </section>

    {loginPending ? <p className="rounded-lg border border-warning/40 bg-warning-subtle p-4 text-sm" role="status">Aguardando a confirmação da OpenAI. Esta tela atualiza automaticamente quando você volta para esta aba.</p> : null}
    {challenge && loginPending && expiredChallenge !== `${challenge.userCode}\0${challenge.expiresAt}` ? <Challenge challenge={challenge} /> : null}
    {challenge && loginPending && expiredChallenge === `${challenge.userCode}\0${challenge.expiresAt}` ? <p className="rounded-md border border-warning/40 bg-warning-subtle p-3 text-sm" role="status">O código expirou. Cancele esta tentativa para iniciar outra.</p> : null}

    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(17rem,0.75fr)]">
      <UsageOverview usage={usage} />
      <ModelsOverview diagnostic={diagnostic} />
    </div>
  </section>;
}
