import { describe, expect, it } from "vitest";

import openapi from "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json" with { type: "json" };

const SNAPSHOT_SHA = "75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34";
const CONFIG_PATHS = [
  "/credit/configuracoes-financeiras",
  "/credit/configuracoes-financeiras/{configuracao_id}",
  "/credit/configuracoes-financeiras/{configuracao_id}/aprovar",
  "/credit/configuracoes-financeiras/{configuracao_id}/ativar",
  "/credit/configuracoes-financeiras/{configuracao_id}/inativar",
  "/credit/configuracoes-financeiras/{configuracao_id}/programar",
  "/credit/configuracoes-financeiras/calendarios",
  "/credit/configuracoes-financeiras/modalidades",
  "/credit/configuracoes-financeiras/snapshots",
  "/credit/configuracoes-financeiras/vigente",
] as const;

const EXPECTED_OPERATIONS = [
  "GET /credit/configuracoes-financeiras",
  "POST /credit/configuracoes-financeiras",
  "GET /credit/configuracoes-financeiras/{configuracao_id}",
  "POST /credit/configuracoes-financeiras/{configuracao_id}/aprovar",
  "POST /credit/configuracoes-financeiras/{configuracao_id}/ativar",
  "POST /credit/configuracoes-financeiras/{configuracao_id}/inativar",
  "POST /credit/configuracoes-financeiras/{configuracao_id}/programar",
  "GET /credit/configuracoes-financeiras/calendarios",
  "POST /credit/configuracoes-financeiras/calendarios",
  "GET /credit/configuracoes-financeiras/modalidades",
  "POST /credit/configuracoes-financeiras/modalidades",
  "POST /credit/configuracoes-financeiras/snapshots",
  "GET /credit/configuracoes-financeiras/vigente",
] as const;
const CONFIGURACOES_OPERATION_COUNT_LABEL = "13 operacoes oficiais";
void CONFIGURACOES_OPERATION_COUNT_LABEL;

type OpenApiParameter = Readonly<{ in?: string; name?: string }>;
type OpenApiOperation = Readonly<{ parameters?: readonly OpenApiParameter[]; security?: unknown }>;

function operations() {
  const result: string[] = [];
  for (const [route, pathItem] of Object.entries(openapi.paths)) {
    for (const method of Object.keys(pathItem)) result.push(`${method.toUpperCase()} ${route}`);
  }
  return result;
}

describe("contrato OpenAPI de Configuracoes Financeiras", () => {
  it("preserva snapshot governado 106/133 e SHA publicado", async () => {
    const { createHash } = await import("node:crypto");
    const { readFile } = await import("node:fs/promises");
    const bytes = await readFile(new URL("../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json", import.meta.url));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(SNAPSHOT_SHA);
    expect(operations()).toHaveLength(106);
    expect(Object.keys(openapi.components.schemas)).toHaveLength(133);
  });

  it("certifica 13 operacoes Bearer com correlation e sem Idempotency-Key", () => {
    expect(operations().filter((operation) => operation.includes("/credit/configuracoes-financeiras")).sort()).toEqual([...EXPECTED_OPERATIONS].sort());
    for (const route of CONFIG_PATHS) {
      const pathItem = openapi.paths[route];
      for (const operation of Object.values(pathItem) as OpenApiOperation[]) {
        expect(operation.security).toEqual([{ BearerAuth: [] }]);
        const headers = operation.parameters?.filter((parameter) => parameter.in === "header").map((parameter) => parameter.name) ?? [];
        expect(headers).toContain("X-Correlation-ID");
        expect(headers).not.toContain("Idempotency-Key");
      }
    }
  });

  it("usa schemas oficiais e estados exatos sem endpoint futuro", () => {
    expect(openapi.components.schemas.ConfiguracaoFinanceiraState.enum).toEqual(["rascunho", "aprovada", "programada", "ativa", "substituida", "inativa"]);
    expect(openapi.components.schemas.ConfiguracaoFinanceiraCreateRequest.required).toEqual(["modalidade", "calendario_id", "vigencia_inicio", "taxas", "parametros", "politica_arredondamento"]);
    expect(openapi.components.schemas.ConfiguracaoFinanceiraResponse.required).toContain("parametros");
    expect(operations().some((operation) => operation.includes("/motor") || operation.includes("/contratos"))).toBe(true);
    expect(operations().filter((operation) => operation.includes("/credit/configuracoes-financeiras"))).not.toContain("POST /credit/configuracoes-financeiras/preview");
  });
});
