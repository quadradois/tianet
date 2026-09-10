import Link from "next/link";

import type { OpenAIReadResult, OpenAIState } from "../../lib/openai/openai-policy";
import { cn } from "../../lib/utils";

type OpenAIBadgeProps = Readonly<{ result: OpenAIReadResult }>;
type BadgeTone = "success" | "warning" | "destructive" | "unavailable";
type BadgePresentation = Readonly<{ label: string; detail: string; tone: BadgeTone }>;

function presentationForState(state: OpenAIState, planType: string | null): BadgePresentation {
  switch (state) {
    case "CONECTADO":
      return { label: "OpenAI conectado", detail: planType ? `Plano ${planType}` : "Conta conectada", tone: "success" };
    case "LIMITE_ATINGIDO":
      return { label: "OpenAI conectado", detail: "Limite de uso atingido", tone: "warning" };
    case "AGUARDANDO_USUARIO":
      return { label: "OpenAI aguardando login", detail: "Concluir conexão", tone: "warning" };
    case "DESCONECTADO":
      return { label: "OpenAI não conectado", detail: "Ver conexão", tone: "destructive" };
    case "DESABILITADO":
      return { label: "OpenAI desabilitado", detail: "Recurso indisponível", tone: "unavailable" };
    case "INDISPONIVEL":
      return { label: "OpenAI indisponível", detail: "Verificar serviço", tone: "unavailable" };
    case "ERRO":
      return { label: "OpenAI com erro", detail: "Verificar conexão", tone: "destructive" };
    case "ERRO_RESULTADO_DESCONHECIDO":
      return { label: "OpenAI requer verificação", detail: "Confirmar estado", tone: "warning" };
  }
}

function presentation(result: OpenAIReadResult): BadgePresentation {
  return result.kind === "ready"
    ? presentationForState(result.connection.state, result.connection.planType)
    : { label: "OpenAI indisponível", detail: "Verificar conexão", tone: "unavailable" };
}

function highestUsage(result: OpenAIReadResult): number | null {
  if (result.kind !== "ready" || result.connection.usageSummary?.rateLimitsStatus !== "ok") return null;
  const values = result.connection.usageSummary.rateLimits.flatMap((limit) =>
    [limit.primary, limit.secondary].flatMap((window) => window ? [window.usedPercent] : []));
  return values.length ? Math.max(...values) : null;
}

function formatObservedAt(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

const borderByTone: Record<BadgeTone, string> = {
  success: "border-border",
  warning: "border-warning/50 bg-warning-subtle",
  destructive: "border-destructive/40 bg-destructive/5",
  unavailable: "border-border bg-muted/60",
};

const dotByTone: Record<BadgeTone, string> = {
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
  unavailable: "bg-muted-foreground",
};

/**
 * Selo operacional da OpenAI. A leitura vem do snapshot local do agent e não
 * dispara diagnóstico nem consulta ao provedor durante a navegação.
 */
export function OpenAIBadge({ result }: OpenAIBadgeProps) {
  const content = presentation(result);
  const usage = highestUsage(result);
  const connected = result.kind === "ready" && result.connection.accountConnected;
  const summary = result.kind === "ready" ? result.connection.usageSummary : null;

  return (
    <Link
      className={cn(
        "flex min-h-(--size-control) items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted",
        borderByTone[content.tone],
      )}
      href="/app/openai"
    >
      <span aria-hidden="true" className={cn("size-2.5 shrink-0 rounded-full", dotByTone[content.tone])} />
      <span className="min-w-0">
        <span className="block font-semibold">{content.label}</span>
        <span className="block truncate text-xs text-muted-foreground">{content.detail}</span>
        {connected && usage !== null ? (
          <span className="mt-1 grid gap-1">
            <span className="block text-xs font-medium text-muted-foreground">Maior uso: {usage}%</span>
            <span aria-hidden="true" className="block h-1 overflow-hidden rounded-full bg-muted">
              <span
                className={cn("block h-full rounded-full", usage >= 90 ? "bg-destructive" : usage >= 70 ? "bg-warning" : "bg-success")}
                style={{ width: `${usage}%` }}
              />
            </span>
            <span className="block text-[0.6875rem] text-muted-foreground">Dados de {formatObservedAt(summary!.observedAt)}</span>
          </span>
        ) : connected && summary?.rateLimitsStatus === "error" ? (
          <span className="mt-1 grid gap-0.5 text-xs text-muted-foreground">
            <span className="font-medium">Limites indisponíveis</span>
            <span className="text-[0.6875rem]">Dados de {formatObservedAt(summary.observedAt)}</span>
          </span>
        ) : connected && summary?.rateLimitsStatus === "ok" ? (
          <span className="mt-1 grid gap-0.5 text-xs text-muted-foreground">
            <span className="font-medium">Nenhuma janela informada</span>
            <span className="text-[0.6875rem]">Dados de {formatObservedAt(summary.observedAt)}</span>
          </span>
        ) : connected ? <span className="mt-1 block text-xs font-medium text-muted-foreground">Limites ainda não consultados</span> : null}
      </span>
    </Link>
  );
}

export function OpenAIBadgePending() {
  return (
    <Link
      className="flex min-h-(--size-control) items-center gap-2 rounded-md border border-border bg-muted/60 px-3 py-2 text-sm hover:bg-muted"
      href="/app/openai"
    >
      <span aria-hidden="true" className="size-2.5 shrink-0 rounded-full bg-muted-foreground" />
      <span className="min-w-0">
        <span className="block font-semibold">OpenAI</span>
        <span className="block truncate text-xs text-muted-foreground">Verificando conexão</span>
      </span>
    </Link>
  );
}
