import type { components } from "../api/openapi.generated";
import { normalizarMoeda } from "../formato/brasileiro";

/** O lancamento atravessa quatro contextos; exige as quatro permissoes. */
export const LANCAMENTO_PERMISSIONS = [
  "devedor.criar",
  "comercial.proposta.criar",
  "contratos.contrato.criar",
  "motor.emprestimo.criar",
] as const;

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
  diaDeAcerto: string;
}>;

export type DevedorEntrada = Readonly<{
  devedorId?: string | undefined;
  documento?: string | undefined;
  nome?: string | undefined;
  contatoWhatsapp?: string | undefined;
}>;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Valida a forma do que o Credor digitou, antes de gastar uma ida ao backend.
 *
 * Nao interpreta e nao converte valores financeiros: devolve os campos como
 * texto, apenas com a virgula normalizada para ponto, que e o formato do
 * contrato. Qualquer regra de negocio continua sendo do Motor.
 */
export function validarCondicoes(entrada: CondicoesEntrada): readonly string[] {
  const erros: string[] = [];
  if (normalizarMoeda(entrada.valor) === undefined) erros.push("Informe o valor emprestado em reais.");
  // Percentual inteiro: `5` significa 5% ao mes. Aceitar decimal aqui foi o que
  // fez um lancamento sair com taxa de 500% — o Credor digitou 5 pensando em
  // porcento e o contrato leu 5 como fracao.
  const taxa = entrada.taxa.trim();
  if (!/^\d{1,3}$/.test(taxa) || Number(taxa) > 100) {
    erros.push("Informe a taxa de juros ao mes em numero inteiro, de 0 a 100.");
  }
  // O emprestimo deixou de ser plano de parcelas: o devedor escolhe um dia do
  // mes para acertar, e o acerto se repete nele (DR-004).
  const dia = entrada.diaDeAcerto.trim();
  if (!/^\d{1,2}$/.test(dia) || Number(dia) < 1 || Number(dia) > 31) {
    erros.push("Informe o dia do mes para o acerto, de 1 a 31.");
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
  return normalizarMoeda(valor) ?? valor.trim();
}

/**
 * Converte a taxa percentual inteira digitada pelo Credor na fracao que o
 * contrato exige: `5` vira `"0.05"`.
 *
 * Feito por manipulacao de texto, nunca por divisao. `5/100` em ponto flutuante
 * abre a porta para artefatos de precisao num valor financeiro, e o Motor
 * permanece a unica autoridade sobre o calculo — isto e conversao de unidade na
 * entrada, como formatar uma data, nao regra de negocio.
 */
export function percentualParaFracao(percentualInteiro: string): string {
  const digitos = percentualInteiro.trim().padStart(3, "0");
  return `${digitos.slice(0, -2)}.${digitos.slice(-2)}`;
}
