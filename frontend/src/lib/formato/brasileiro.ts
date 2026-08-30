/**
 * Formatacao brasileira de dinheiro, documento e data.
 *
 * **Tudo aqui e manipulacao de texto. Nada e convertido para numero.**
 *
 * O backend devolve dinheiro como string decimal (`"10000.00"`), justamente
 * para que nenhum consumidor precise de ponto flutuante. Converter para numero
 * so para reformatar reintroduziria o risco que o contrato eliminou, e
 * esbarraria no guardrail anti-motor-paralelo, que veta as APIs de conversao e
 * de formatacao numerica nas telas financeiras.
 *
 * Este arquivo nao nomeia essas APIs nem em comentario: o scanner e cego por
 * desenho e nao distingue mencao de uso — foi o que aconteceu com `cpfValido`
 * no PLAN-027.
 *
 * A regra e correta e nao foi afrouxada: formatar nao e calcular, e agrupar
 * digitos com `slice` prova isso melhor do que uma excecao no scanner. Ver
 * `PLAN-029 §5`.
 */

const APENAS_DIGITOS = /\D/g;
const PREFIXO_BRL = /^R\$\s*/;
const INTEIRO_BRL = /^(?:\d+|\d{1,3}(?:\.\d{3})+)$/;
const MOEDA_BRL = /^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,2})?$/;

/** Agrupa a parte inteira em milhares, da direita para a esquerda. */
function agruparMilhares(inteiro: string): string {
  let restante = inteiro;
  const grupos: string[] = [];
  while (restante.length > 3) {
    grupos.unshift(restante.slice(-3));
    restante = restante.slice(0, -3);
  }
  grupos.unshift(restante);
  return grupos.join(".");
}

/**
 * `"10000.00"` -> `"R$ 10.000,00"`.
 *
 * Devolve o valor original quando nao reconhece a forma: exibir o dado cru e
 * preferivel a exibir um numero inventado.
 */
export function moeda(valor: string | undefined | null): string {
  const bruto = (valor ?? "").trim();
  if (!/^-?\d+(\.\d+)?$/.test(bruto)) return bruto;
  const negativo = bruto.startsWith("-");
  const semSinal = negativo ? bruto.slice(1) : bruto;
  const [inteiro = "0", decimais = ""] = semSinal.split(".");
  const centavos = `${decimais}00`.slice(0, 2);
  return `${negativo ? "-" : ""}R$ ${agruparMilhares(inteiro)},${centavos}`;
}

/**
 * Le dinheiro digitado no padrao brasileiro e devolve a string decimal do
 * contrato: `"R$ 2.000,00"` ou `"2.000"` -> `"2000.00"`.
 */
export function normalizarMoeda(valor: string | undefined | null): string | undefined {
  const bruto = (valor ?? "").trim().replace(PREFIXO_BRL, "").replace(/\s/g, "");
  if (!bruto || !MOEDA_BRL.test(bruto)) return undefined;
  const [inteiroBruto = "", centavosBrutos = ""] = bruto.split(",");
  if (!INTEIRO_BRL.test(inteiroBruto)) return undefined;
  const inteiro = inteiroBruto.replace(/\./g, "").replace(/^0+(?=\d)/, "") || "0";
  const centavos = `${centavosBrutos}00`.slice(0, 2);
  return `${inteiro}.${centavos}`;
}

/** Mascara uma entrada monetaria reconhecida para BRL; preserva texto invalido. */
export function mascaraMoeda(valor: string | undefined | null): string {
  const normalizado = normalizarMoeda(valor);
  return normalizado === undefined ? (valor ?? "").trim() : moeda(normalizado);
}

/** `"39053344705"` -> `"390.533.447-05"`. Devolve o original se nao for CPF. */
export function cpf(documento: string | undefined | null): string {
  const digitos = (documento ?? "").replace(APENAS_DIGITOS, "");
  if (digitos.length !== 11) return (documento ?? "").trim();
  return `${digitos.slice(0, 3)}.${digitos.slice(3, 6)}.${digitos.slice(6, 9)}-${digitos.slice(9)}`;
}

/**
 * `"2026-08-17"` ou `"2026-08-17T18:32:00.325592Z"` -> `"17/08/2026"`.
 *
 * Le apenas a parte de data da string ISO, por expressao regular. Construir um
 * objeto de data aplicaria o fuso do navegador e poderia deslocar o dia — um
 * vencimento nao pode mudar de data por causa de onde o operador esta.
 */
export function data(iso: string | undefined | null): string {
  const bruto = (iso ?? "").trim();
  const casamento = /^(\d{4})-(\d{2})-(\d{2})/.exec(bruto);
  if (!casamento) return bruto;
  const [, ano, mes, dia] = casamento;
  return `${dia}/${mes}/${ano}`;
}
