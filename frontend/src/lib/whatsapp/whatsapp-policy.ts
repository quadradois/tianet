import type { components } from "../api/openapi.generated";

export const WHATSAPP_READ_PERMISSION = "whatsapp.conexao.ler" as const;
export const WHATSAPP_MANAGE_PERMISSION = "whatsapp.conexao.gerir" as const;

export type WhatsAppPermission = typeof WHATSAPP_READ_PERMISSION | typeof WHATSAPP_MANAGE_PERMISSION;

export type WhatsAppConnection = components["schemas"]["ConexaoWhatsAppResponse"];
export type WhatsAppQrCode = components["schemas"]["QrCodeConexaoResponse"];

export type WhatsAppActionState =
  | Readonly<{ kind: "idle" }>
  | Readonly<{ kind: "success"; message: string; correlationId: string; qrcode?: string | null }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export type WhatsAppReadResult =
  | Readonly<{ kind: "ready"; connection: WhatsAppConnection }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export const INITIAL_WHATSAPP_ACTION_STATE: WhatsAppActionState = { kind: "idle" };

/**
 * Os estados que a tela sabe desenhar.
 *
 * `ausente` e `pendente` sao coisas DIFERENTES para quem opera, ainda que o selo
 * da barra lateral agrupe as duas em "nao conectado": ausente pede criar a
 * instancia, pendente pede escanear o QR que ja existe. Uma flag so faria a tela
 * oferecer a acao errada em metade dos casos.
 *
 * O selo pode simplificar porque ele so avisa; a tela nao pode, porque ela age.
 */
export type WhatsAppScreenState = "ausente" | "pendente" | "conectada";

export function screenState(connection: WhatsAppConnection): WhatsAppScreenState {
  if (!connection.existe) return "ausente";
  return connection.pareada ? "conectada" : "pendente";
}

export function hasExactPermission(granted: readonly string[], permission: WhatsAppPermission): boolean {
  return granted.includes(permission);
}

export function isWhatsAppConnection(value: unknown): value is WhatsAppConnection {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record.existe === "boolean"
    && typeof record.pareada === "boolean"
    && typeof record.conectado === "boolean"
    && (record.numero === null || record.numero === undefined || typeof record.numero === "string")
    && (record.nome_exibicao === null || record.nome_exibicao === undefined || typeof record.nome_exibicao === "string")
    && (record.instancia_nome === null || record.instancia_nome === undefined || typeof record.instancia_nome === "string");
}

export function isWhatsAppQrCode(value: unknown): value is WhatsAppQrCode {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return record.qrcode_base64 === null || record.qrcode_base64 === undefined || typeof record.qrcode_base64 === "string";
}
