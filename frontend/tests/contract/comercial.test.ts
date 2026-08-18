import { describe, expect, it } from "vitest";

import spec from "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json" with { type: "json" };

const SNAPSHOT_SHA256 = "ba4342af3a977fe65e0f0af60d7e6fd7cab219b386a4f9c03b9167051a1c02cd";
type HttpMethod = "get" | "patch" | "post";
type OpenApiParameter = Readonly<{ name: string }>;
type OpenApiOperation = Readonly<{
  parameters?: readonly OpenApiParameter[];
  responses: Record<string, unknown>;
  security?: readonly Record<string, readonly unknown[]>[];
}>;
type OpenApiSpec = Readonly<{
  components: Readonly<{ schemas: Record<string, unknown> }>;
  paths: Record<string, Partial<Record<HttpMethod, OpenApiOperation>>>;
}>;
const openapi = spec as OpenApiSpec;

const OPERATIONS = [
  ["post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais", 201, ["400", "401", "403", "404", "422", "500"]],
  ["get", "/credit/simulacoes-comerciais/{simulacao_id}", 200, ["400", "401", "403", "404", "500"]],
  ["post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais", 201, ["400", "401", "403", "404", "422", "500"]],
  ["get", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais", 200, ["400", "401", "403", "404", "500"]],
  ["get", "/credit/propostas-comerciais/{proposta_id}", 200, ["400", "401", "403", "404", "500"]],
  ["patch", "/credit/propostas-comerciais/{proposta_id}", 200, ["400", "401", "403", "404", "422", "500"]],
  ["post", "/credit/propostas-comerciais/{proposta_id}/enviar-para-analise", 200, ["400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/propostas-comerciais/{proposta_id}/aprovar", 200, ["400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/propostas-comerciais/{proposta_id}/recusar", 200, ["400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/propostas-comerciais/{proposta_id}/cancelar", 200, ["400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/propostas-comerciais/{proposta_id}/expirar", 200, ["400", "401", "403", "404", "409", "500"]],
  ["get", "/credit/propostas-comerciais/{proposta_id}/contrato-logico", 200, ["400", "401", "403", "404", "422", "500"]],
] as const;

describe("contrato OpenAPI Comercial", () => {
  it("mantem inventario 108/137 e SHA governado", async () => {
    const { createHash } = await import("node:crypto");
    const { readFile } = await import("node:fs/promises");
    const bytes = await readFile(new URL("../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json", import.meta.url));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(SNAPSHOT_SHA256);
    expect(Object.values(openapi.paths).flatMap((pathItem) => Object.keys(pathItem))).toHaveLength(108);
    expect(Object.keys(openapi.components.schemas)).toHaveLength(137);
  });

  it("publica exatamente as 12 operacoes Comerciais esperadas", () => {
    for (const [method, route, success, errors] of OPERATIONS) {
      const operation = openapi.paths[route]?.[method];
      expect(operation, `${method.toUpperCase()} ${route}`).toBeTruthy();
      if (!operation) throw new Error(`Operacao ausente: ${method.toUpperCase()} ${route}`);
      expect(operation.security).toEqual([{ BearerAuth: [] }]);
      expect(operation.responses[String(success)]).toBeTruthy();
      for (const status of errors) expect(operation.responses[status], `${route} ${status}`).toBeTruthy();
      expect(operation.parameters?.some((parameter) => parameter.name === "X-Correlation-ID")).toBe(true);
      expect(operation.parameters?.some((parameter) => parameter.name === "Idempotency-Key")).toBe(false);
    }
  });

  it("mantem schemas oficiais e nao publica trilha detalhada inexistente", () => {
    for (const schema of [
      "SimulacaoComercialCreateRequest",
      "SimulacaoComercialResponse",
      "PropostaComercialCreateRequest",
      "PropostaComercialUpdateRequest",
      "PropostaComercialResponse",
      "PropostaComercialListagemResponse",
      "DecisaoComercialRequest",
      "PropostaAprovadaLogicaResponse",
    ]) {
      expect(openapi.components.schemas[schema]).toBeTruthy();
    }
    expect(Object.keys(openapi.paths).filter((route) => route.includes("comerciais")).join("\n")).not.toMatch(/decisoes-comerciais|trilha/i);
    expect(Object.keys(openapi.components.schemas).join("\n")).not.toMatch(/Trilha|DecisaoComercialTrail/i);
  });
});
