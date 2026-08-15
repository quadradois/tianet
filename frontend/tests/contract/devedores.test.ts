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

const devedores = "/credit/carteiras/{carteira_id}/devedores";
const devedor = "/credit/carteiras/{carteira_id}/devedores/{devedor_id}";
const historico = "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/historico";
const inativar = "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/inativar";
const reativar = "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/reativar";

function operation(pathname: string, method: string) {
  return record(record(paths[pathname])[method]);
}

function header(operationValue: Record<string, unknown>, name: string) {
  const parameters = operationValue.parameters;
  if (!Array.isArray(parameters)) throw new Error("parameters esperado");
  return parameters.find((item) => record(item).name === name);
}

describe("contratos da jornada Devedores", () => {
  it("usa exatamente os sete endpoints oficiais e schemas certificados", () => {
    expect(operation(devedores, "get").security).toEqual([{ BearerAuth: [] }]);
    expect(operation(devedores, "post").security).toEqual([{ BearerAuth: [] }]);
    expect(operation(devedor, "get").security).toEqual([{ BearerAuth: [] }]);
    expect(operation(devedor, "patch").security).toEqual([{ BearerAuth: [] }]);
    expect(operation(historico, "get").security).toEqual([{ BearerAuth: [] }]);
    expect(operation(inativar, "post").security).toEqual([{ BearerAuth: [] }]);
    expect(operation(reativar, "post").security).toEqual([{ BearerAuth: [] }]);
    for (const schema of ["DevedorCreateRequest", "DevedorUpdateRequest", "DevedorResponse", "DevedorListagemResponse", "DevedorHistoricoResponse", "ContatoPayload"]) {
      expect(schemas[schema]).toBeDefined();
    }
  });

  it("documenta consulta por documento somente na rota de listagem", () => {
    const get = operation(devedores, "get");
    expect(header(get, "documento")).toEqual(expect.objectContaining({ in: "query", name: "documento", required: false }));
    expect(record(record(record(record(record(get.responses)["200"]).content)["application/json"]).schema).anyOf).toBeDefined();
    expect(paths["/credit/carteiras/{carteira_id}/devedores/documentos/{documento}"]).toBeUndefined();
  });

  it("exige Idempotency-Key apenas nos quatro comandos", () => {
    for (const op of [operation(devedores, "post"), operation(devedor, "patch"), operation(inativar, "post"), operation(reativar, "post")]) {
      expect(header(op, "Idempotency-Key")).toEqual(expect.objectContaining({ in: "header", required: true }));
    }
    for (const op of [operation(devedores, "get"), operation(devedor, "get"), operation(historico, "get")]) {
      expect(header(op, "Idempotency-Key")).toBeUndefined();
    }
  });

  it("preserva matriz de status e ErroResponse sem inventar Comercial", () => {
    expect(Object.keys(record(operation(devedores, "post").responses)).sort()).toEqual(["201", "400", "401", "403", "404", "409", "422", "500"]);
    expect(Object.keys(record(operation(devedor, "patch").responses)).sort()).toEqual(["200", "400", "401", "403", "404", "422", "500"]);
    expect(Object.keys(record(operation(devedores, "get").responses)).sort()).toEqual(["200", "400", "401", "403", "404", "500"]);
    for (const pathname of [devedores, devedor, historico, inativar, reativar]) {
      const methods = record(paths[pathname]);
      for (const value of Object.values(methods).map(record)) {
        for (const [status, response] of Object.entries(record(value.responses))) {
          if (status.startsWith("2")) continue;
          expect(record(record(record(record(response).content)["application/json"]).schema).$ref).toBe("#/components/schemas/ErroResponse");
        }
      }
    }
    expect(paths["/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais"]).toBeDefined();
  });
});
