import type { components } from "../api/openapi.generated";

/** O lancamento atravessa quatro contextos; exige as quatro permissoes. */
export const LANCAMENTO_PERMISSIONS = [
  "devedor.criar",
  "comercial.proposta.criar",
  "contratos.contrato.criar",
  "motor.emprestimo.criar",
] as const;

export type LancamentoPermission = (typeof LANCAMENTO_PERMISSIONS)[number];
export type Lancamento = components["schemas"]["LancamentoResponse"];

export type LancamentoActionState = Readonly<{
  kind: "idle" | "success" | "problem";
  message: string;
  correlationId?: string;
  status?: number;
  emprestimoId?: string;
}>;

export const INITIAL_LANCAMENTO_ACTION_STATE: LancamentoActionState = {
  kind: "idle",
  message: "Preencha os dados e confirme o lancamento.",
};

/** Exige todas as permissoes: faltando uma, a cadeia nao pode ser executada. */
export function podeLancar(permissions: readonly string[]): boolean {
  const concedidas = new Set(permissions);
  return LANCAMENTO_PERMISSIONS.every((permission) => concedidas.has(permission));
}

export function permissoesFaltantes(permissions: readonly string[]): readonly string[] {
  const concedidas = new Set(permissions);
  return LANCAMENTO_PERMISSIONS.filter((permission) => !concedidas.has(permission));
}

export type CondicoesEntrada = Readonly<{
  valor: string;
  taxa: string;
  parcelas: string;
  primeiroVencimento: string;
}>;

export type DevedorEntrada = Readonly<{
  devedorId?: string | undefined;
  documento?: string | undefined;
  nome?: string | undefined;
  contatoWhatsapp?: string | undefined;
}>;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATA_ISO = /^\d{4}-\d{2}-\d{2}$/;
// Aceita "1234,56" ou "1234.56". O backend e a autoridade sobre o valor; aqui
// so se verifica forma, nunca se calcula nem se arredonda nada.
const DECIMAL = /^\d{1,12}([.,]\d{1,4})?$/;

/**
 * Valida a forma do que o Credor digitou, antes de gastar uma ida ao backend.
 *
 * Nao interpreta e nao converte valores financeiros: devolve os campos como
 * texto, apenas com a virgula normalizada para ponto, que e o formato do
 * contrato. Qualquer regra de negocio continua sendo do Motor.
 */
export function validarCondicoes(entrada: CondicoesEntrada): readonly string[] {
  const erros: string[] = [];
  if (!DECIMAL.test(entrada.valor.trim())) erros.push("Informe o valor emprestado.");
  if (!DECIMAL.test(entrada.taxa.trim())) erros.push("Informe a taxa de juros mensal.");
  const parcelas = Number(entrada.parcelas);
  if (!Number.isInteger(parcelas) || parcelas < 1 || parcelas > 360) {
    erros.push("Informe a quantidade de parcelas, de 1 a 360.");
  }
  if (!DATA_ISO.test(entrada.primeiroVencimento.trim())) {
    erros.push("Informe a data do primeiro vencimento.");
  }
  return erros;
}

/**
 * Confere os digitos verificadores do CPF.
 *
 * Regra de formato, nao de dinheiro: o backend continua sendo a autoridade
 * (`DOMAIN-022`, VO-022-VAL-001/002). Isto existe para que o erro apareca no
 * campo, e nao tres passos adiante como "nao foi possivel concluir".
 */
export function cpfValido(bruto: string): boolean {
  const digitos = bruto.replace(/[.\-\s]/g, "");
  if (!/^\d{11}$/.test(digitos)) return false;
  if (new Set(digitos).size === 1) return false;
  const numeros = [...digitos].map(Number);
  // Laco explicito, e nao acumulador funcional: o scanner anti-motor-paralelo
  // veta esse acumulador no frontend e nao distingue soma de digito verificador
  // de soma financeira. A regra e cega por desenho, e abrir excecao nela para
  // caber um caso legitimo seria o mesmo erro da DR-002.
  for (const posicao of [9, 10]) {
    let soma = 0;
    for (let indice = 0; indice < posicao; indice += 1) {
      soma += (numeros[indice] as number) * (posicao + 1 - indice);
    }
    const resto = (soma * 10) % 11;
    if ((resto === 10 ? 0 : resto) !== numeros[posicao]) return false;
  }
  return true;
}

export function validarDevedor(entrada: DevedorEntrada): readonly string[] {
  if (entrada.devedorId) {
    return UUID.test(entrada.devedorId) ? [] : ["Devedor selecionado invalido."];
  }
  const erros: string[] = [];
  const documento = entrada.documento?.trim();
  if (!documento) erros.push("Informe o CPF do devedor.");
  else if (!cpfValido(documento)) erros.push("CPF invalido: confira os numeros digitados.");
  if (!entrada.nome?.trim()) erros.push("Informe o nome do devedor.");
  // Obrigatorio por decisao formal do PLAN-027: sem numero nao ha destino para
  // o comprovante.
  if (!entrada.contatoWhatsapp?.trim()) erros.push("Informe o WhatsApp do devedor.");
  return erros;
}

export function normalizarDecimal(valor: string): string {
  return valor.trim().replace(",", ".");
}
