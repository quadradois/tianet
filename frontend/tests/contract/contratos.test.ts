import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const currentDir = dirname(fileURLToPath(import.meta.url));
const snapshotPath = resolve(currentDir, "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json");
const raw = readFileSync(snapshotPath);
const spec = JSON.parse(raw.toString("utf8")) as {
  paths: Record<string, Record<string, { parameters?: { in: string; name: string; required?: boolean }[]; requestBody?: unknown; responses: Record<string, unknown>; security?: Record<string, string[]>[] }>>;
  components: { schemas: Record<string, unknown> };
};

const CONTRACT_OPERATIONS = [
  ["get", "/credit/carteiras/{carteira_id}/contratos", ["200", "400", "401", "403", "404", "500"]],
  ["post", "/credit/carteiras/{carteira_id}/contratos", ["201", "400", "401", "403", "404", "409", "422", "500"]],
  ["get", "/credit/contratos/{contrato_id}", ["200", "400", "401", "403", "404", "500"]],
  ["get", "/credit/contratos/{contrato_id}/historico", ["200", "400", "401", "403", "404", "500"]],
  ["post", "/credit/contratos/{contrato_id}/assinar", ["200", "400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/contratos/{contrato_id}/liberar-para-motor", ["200", "400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/contratos/{contrato_id}/cancelar", ["200", "400", "401", "403", "404", "409", "500"]],
  ["post", "/credit/contratos/{contrato_id}/encerrar", ["200", "400", "401", "403", "404", "409", "500"]],
] as const;

describe("Contrato OpenAPI consumido pelo frontend", () => {
  it("preserva snapshot oficial 108/137 e SHA governado", () => {
    const operationCount = Object.values(spec.paths).flatMap((item) => Object.keys(item).filter((method) => ["get", "post", "patch", "put", "delete"].includes(method))).length;
    expect(operationCount).toBe(108);
    expect(Object.keys(spec.components.schemas)).toHaveLength(137);
    expect(createHash("sha256").update(raw).digest("hex")).toBe("6b24001ab24f9e4c47764d93fa8c640115dedd2f77bbc0df290d4145934b953d");
  });

  it("certifica as 8 operacoes de Contratos sem Idempotency-Key", () => {
    for (const [method, path, responses] of CONTRACT_OPERATIONS) {
      const operation = spec.paths[path]?.[method];
      expect(operation, `${method.toUpperCase()} ${path}`).toBeTruthy();
      if (!operation) throw new Error(`${method.toUpperCase()} ${path} ausente`);
      expect(operation.security).toEqual([{ BearerAuth: [] }]);
      expect(Object.keys(operation.responses)).toEqual(responses);
      expect(operation.parameters?.some((parameter) => parameter.in === "header" && parameter.name === "X-Correlation-ID")).toBe(true);
      expect(operation.parameters?.some((parameter) => parameter.name === "Idempotency-Key")).toBe(false);
    }
  });

  it("mantem Motor e contrato logico Comercial fora do recorte IMP-293", () => {
    expect(spec.paths["/credit/contratos/{contrato_id}/emprestimos"]?.post).toBeTruthy();
    expect(spec.paths["/credit/propostas-comerciais/{proposta_id}/contrato-logico"]?.get).toBeTruthy();
    expect(CONTRACT_OPERATIONS.map(([, path]) => path)).not.toContain("/credit/contratos/{contrato_id}/emprestimos");
    expect(CONTRACT_OPERATIONS.map(([, path]) => path)).not.toContain("/credit/propostas-comerciais/{proposta_id}/contrato-logico");
  });

  it("schemas de Contratos preservam estados e objetos opacos", () => {
    expect(spec.components.schemas.ContratoCreditoState).toMatchObject({ enum: ["rascunho", "formalizado", "assinado", "liberado_para_motor", "cancelado", "encerrado"] });
    expect(JSON.stringify(spec.components.schemas.ContratoCreditoCreateRequest)).toContain("proposta_comercial_id");
    expect(JSON.stringify(spec.components.schemas.ContratoCreditoResponse)).toContain("total_eventos");
    expect(JSON.stringify(spec.components.schemas.ContratoLiberadoLogicoResponse)).toContain("parametros_contratados");
  });
});
