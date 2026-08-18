import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

function record(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error("objeto esperado");
  return Object.fromEntries(Object.entries(value));
}

const snapshot: unknown = JSON.parse(readFileSync(resolve("../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json"), "utf8"));
const root = record(snapshot);
const paths = record(root.paths);
const schemas = record(record(root.components).schemas);

const operations = [
  ["/credit/carteiras/{carteira_id}/relatorios/resumo", "ResumoCarteiraResponse"],
  ["/credit/carteiras/{carteira_id}/relatorios/vencimentos", "VencimentosInadimplenciaResponse"],
  ["/credit/agenda", "AgendaOperacionalResponse"],
  ["/credit/cobrancas/casos", "FilaCobrancaResponse"],
] as const;

describe("contratos do Dashboard", () => {
  it("usa somente os quatro GETs Bearer e schemas certificados", () => {
    for (const [path, schemaName] of operations) {
      const operation = record(record(paths[path]).get);
      expect(operation.security).toEqual([{ BearerAuth: [] }]);
      expect(record(record(record(record(record(operation.responses)["200"]).content)["application/json"]).schema).$ref).toBe(`#/components/schemas/${schemaName}`);
      expect(Object.keys(record(operation.responses)).sort()).toEqual(["200", "400", "401", "403", "404", "500"]);
      expect(schemas[schemaName]).toBeDefined();
    }
  });

  it("exige data_referencia nos relatorios e governa a janela da agenda", () => {
    for (const path of operations.slice(0, 2).map(([value]) => value)) {
      const parameters = record(record(paths[path]).get).parameters;
      expect(Array.isArray(parameters)).toBe(true);
      expect(parameters).toEqual(expect.arrayContaining([expect.objectContaining({ in: "query", name: "data_referencia", required: true })]));
    }
    const agendaParameters = record(record(paths["/credit/agenda"]).get).parameters;
    expect(agendaParameters).toEqual(expect.arrayContaining([
      expect.objectContaining({ in: "query", name: "carteira_id" }),
      expect.objectContaining({ in: "query", name: "janela_inicio" }),
      expect.objectContaining({ in: "query", name: "janela_fim" }),
    ]));
  });

  it("mantem strings monetarias e identidade explicita nas respostas", () => {
    const summary = record(schemas.ResumoCarteiraResponse);
    const summaryProperties = record(summary.properties);
    expect(record(summaryProperties.principal_a_receber).type).toBe("string");
    expect(record(summaryProperties.total_realizado).type).toBe("string");
    expect(summary.required).toEqual(expect.arrayContaining(["tenant_id", "carteira_id", "data_referencia"]));
    const collectionItem = record(schemas.CobrancaCasoResponse);
    expect(record(record(collectionItem.properties).total_pendente).type).toBe("string");
  });
});
