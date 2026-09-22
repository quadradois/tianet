import type { components } from "../api/openapi.generated";

export const MERCADOPAGO_PERMISSION = "mercadopago.configurar" as const;

export type MercadoPagoConfig = components["schemas"]["ConfiguracaoMercadoPagoResponse"];

export type MercadoPagoReadResult =
  | Readonly<{ kind: "ready"; config: MercadoPagoConfig }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

/**
 * `operacao` distingue os quatro sucessos que a tela precisa narrar de forma
 * diferente: gravar credencial, testar, ligar e desligar. Sem o campo, "salvo
 * com sucesso" apareceria igual depois de desligar a integracao — o oposto do
 * que o operador acabou de fazer.
 */
export type MercadoPagoActionState =
  | Readonly<{ kind: "idle" }>
  | Readonly<{
      kind: "success";
      message: string;
      correlationId: string;
      operacao: "credenciais" | "testar" | "habilitar" | "desabilitar";
      config: MercadoPagoConfig;
    }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export const INITIAL_MERCADOPAGO_ACTION_STATE: MercadoPagoActionState = { kind: "idle" };

/**
 * Estados que a tela sabe desenhar, na ordem em que o operador os percorre.
 *
 * `desligada` e `sem_credencial` sao coisas diferentes: a primeira tem tudo
 * pronto e so precisa do interruptor; a segunda precisa de dados. Agrupar as
 * duas ofereceria o botao errado em metade dos casos.
 */
export type MercadoPagoScreenState =
  | "sem_credencial"
  | "sem_teste"
  | "desligada"
  | "ligada";

export function screenState(config: MercadoPagoConfig): MercadoPagoScreenState {
  if (config.habilitado) return "ligada";
  if (!config.credencial_configurada || !config.assinatura_configurada) return "sem_credencial";
  if (config.testado_em === null) return "sem_teste";
  return "desligada";
}

export function isMercadoPagoConfig(value: unknown): value is MercadoPagoConfig {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.habilitado === "boolean"
    && typeof candidate.credencial_configurada === "boolean"
    && typeof candidate.assinatura_configurada === "boolean"
  );
}

export function hasMercadoPagoPermission(permissoes: readonly string[]): boolean {
  return permissoes.includes(MERCADOPAGO_PERMISSION);
}


export type ChavePix = components["schemas"]["ChavePixResponse"];

export type ChavePixReadResult =
  | Readonly<{ kind: "ready"; chave: ChavePix }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export type ChavePixActionState =
  | Readonly<{ kind: "idle" }>
  | Readonly<{ kind: "success"; message: string; correlationId: string; chave: ChavePix }>
  | Readonly<{ kind: "problem"; message: string; status: number; correlationId: string }>;

export const INITIAL_CHAVE_PIX_ACTION_STATE: ChavePixActionState = { kind: "idle" };

export const TIPOS_CHAVE_PIX = ["cpf", "cnpj", "telefone", "email", "aleatoria"] as const;

export function isChavePix(value: unknown): value is ChavePix {
  if (typeof value !== "object" || value === null) return false;
  return typeof (value as Record<string, unknown>).configurada === "boolean";
}
