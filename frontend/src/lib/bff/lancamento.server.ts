import "server-only";

import type { components } from "../api/openapi.generated";
import { createBackendClient } from "../api/client.server";
import {
  normalizarDecimal,
  podeLancar,
  validarCondicoes,
  validarDevedor,
  type Lancamento,
  type LancamentoActionState,
} from "../lancamento/lancamento-policy";

import {
  ApiProblem,
  correlationId,
  createCookieAuthenticatedFetch,
  idempotencyKey,
  type BffDependencies,
} from "./backend.server";
import type { OperationalContext } from "./context.server";
import type { CookieStore } from "./session.server";

type LancamentoCreateRequest = components["schemas"]["LancamentoCreateRequest"];

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function texto(formData: FormData, chave: string, max: number): string | undefined {
  const valor = formData.get(chave);
  if (typeof valor !== "string") return undefined;
  const limpo = valor.trim();
  if (!limpo || limpo.length > max) return undefined;
  return limpo;
}

function problema(problem: ApiProblem): LancamentoActionState {
  return {
    kind: "problem",
    message: problem.mensagem,
    correlationId: problem.correlationId,
    status: problem.status,
  };
}

function invalido(mensagem: string): LancamentoActionState {
  return { kind: "problem", message: mensagem, status: 400, correlationId: correlationId() };
}

function respostaValida(valor: unknown, context: OperationalContext): valor is Lancamento {
  if (typeof valor !== "object" || valor === null) return false;
  const dados = valor as Record<string, unknown>;
  const identificadores = ["devedor_id", "proposta_id", "contrato_id", "emprestimo_id"];
  void context;
  return (
    identificadores.every(
      (chave) => typeof dados[chave] === "string" && UUID_PATTERN.test(dados[chave] as string),
    ) && Number.isInteger(dados.quantidade_parcelas)
  );
}

/**
 * Lanca o emprestimo em uma unica chamada ao backend.
 *
 * A validacao daqui e de forma, para nao gastar ida ao servidor com campo vazio.
 * Nenhum valor financeiro e calculado, convertido ou arredondado: os campos
 * seguem como texto, so com a virgula normalizada para ponto, e o Motor
 * permanece autoridade sobre o resultado.
 */
export async function criarLancamento(
  cookies: CookieStore,
  context: OperationalContext,
  formData: FormData,
  dependencies: BffDependencies,
): Promise<LancamentoActionState> {
  const requestCorrelation = correlationId();
  if (!podeLancar(context.permissoes)) {
    return problema(
      new ApiProblem({
        status: 403,
        codigo: "acesso_negado",
        mensagem: "Lancamento indisponivel para este acesso.",
        correlationId: requestCorrelation,
      }),
    );
  }

  const devedorId = texto(formData, "devedor_id", 36);
  const entradaDevedor = devedorId
    ? { devedorId }
    : {
        documento: texto(formData, "documento", 32),
        nome: texto(formData, "nome", 200),
        contatoWhatsapp: texto(formData, "contato_whatsapp", 20),
      };
  const errosDevedor = validarDevedor(entradaDevedor);
  const primeiroErroDevedor = errosDevedor[0];
  if (primeiroErroDevedor) return invalido(primeiroErroDevedor);

  const condicoes = {
    valor: texto(formData, "valor", 32) ?? "",
    taxa: texto(formData, "taxa", 32) ?? "",
    parcelas: texto(formData, "parcelas", 8) ?? "",
    primeiroVencimento: texto(formData, "primeiro_vencimento", 10) ?? "",
  };
  const errosCondicoes = validarCondicoes(condicoes);
  const primeiroErroCondicoes = errosCondicoes[0];
  if (primeiroErroCondicoes) return invalido(primeiroErroCondicoes);

  const dataReferencia = texto(formData, "data_referencia", 10) ?? condicoes.primeiroVencimento;

  const body: LancamentoCreateRequest = {
    condicoes: {
      valor_contratado: normalizarDecimal(condicoes.valor),
      taxa_juros_mensal: normalizarDecimal(condicoes.taxa),
      quantidade_parcelas: Number(condicoes.parcelas),
      primeiro_vencimento: condicoes.primeiroVencimento,
      moeda: "BRL",
    },
    data_referencia: dataReferencia,
    ...(devedorId
      ? { devedor_id: devedorId }
      : {
          devedor_novo: {
            documento: entradaDevedor.documento as string,
            nome: entradaDevedor.nome as string,
            contato_whatsapp: entradaDevedor.contatoWhatsapp as string,
          },
        }),
  };

  try {
    const authenticatedFetch = await createCookieAuthenticatedFetch(
      cookies,
      dependencies,
      requestCorrelation,
    );
    const client = createBackendClient(dependencies.config.backendUrl, {
      fetch: authenticatedFetch,
    });
    const resultado = await client.POST("/credit/carteiras/{carteira_id}/lancamentos", {
      body,
      params: {
        path: { carteira_id: context.carteira_padrao.id },
        header: {
          "X-Correlation-ID": requestCorrelation,
          // Uma intencao, uma chave: reenvio da mesma tela nao duplica divida.
          "Idempotency-Key": idempotencyKey(true, texto(formData, "idempotency_key", 255)) as string,
        },
      },
    });

    if (resultado.response.status !== 201) {
      const correlacao =
        resultado.response.headers.get("X-Correlation-ID") ?? requestCorrelation;
      return problema(
        new ApiProblem({
          status: resultado.response.status,
          codigo: "lancamento_recusado",
          mensagem: "Nao foi possivel concluir o lancamento.",
          correlationId: correlacao,
        }),
      );
    }
    if (!respostaValida(resultado.data, context)) {
      return problema(
        new ApiProblem({
          status: 502,
          codigo: "resposta_backend_invalida",
          mensagem: "Servico temporariamente indisponivel.",
          correlationId: requestCorrelation,
        }),
      );
    }

    return {
      kind: "success",
      message: "Emprestimo lancado.",
      correlationId: resultado.response.headers.get("X-Correlation-ID") ?? requestCorrelation,
      emprestimoId: (resultado.data as Lancamento).emprestimo_id,
    };
  } catch (error) {
    if (error instanceof ApiProblem) return problema(error);
    return problema(
      new ApiProblem({
        status: 502,
        codigo: "backend_indisponivel",
        mensagem: "Servico temporariamente indisponivel.",
        correlationId: requestCorrelation,
      }),
    );
  }
}
