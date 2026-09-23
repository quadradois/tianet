import type { components } from "../api/openapi.generated";

export const AGENT_READ_PERMISSION = "agent.inbox.ler" as const;

export type AgentPermission = typeof AGENT_READ_PERMISSION;

export type AgentInbox = components["schemas"]["InboxAgenteResponse"];
export type AgentInboxEntry = components["schemas"]["EntradaInboxResponse"];

export type AgentReadResult =
  | Readonly<{ kind: "ready"; inbox: AgentInbox }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export function hasExactPermission(granted: readonly string[], permission: AgentPermission): boolean {
  return granted.includes(permission);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isAgentInboxEntry(value: unknown): value is AgentInboxEntry {
  if (!isRecord(value)) return false;
  return typeof value.provider_input_id === "string"
    && typeof value.remetente_normalizado === "string"
    && typeof value.classe === "string"
    && (value.texto === null || value.texto === undefined || typeof value.texto === "string")
    && typeof value.estado === "string"
    && typeof value.recebido_em === "string";
}

export function isAgentInbox(value: unknown): value is AgentInbox {
  if (!isRecord(value)) return false;
  if (typeof value.total !== "number" || typeof value.operadora !== "number" || typeof value.devedor !== "number" || typeof value.pre_cadastro !== "number") return false;
  if (!Array.isArray(value.recentes)) return false;
  return value.recentes.every(isAgentInboxEntry);
}
