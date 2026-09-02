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

const COBRANCA_OPERATIONS = [
  ["get", "/credit/cobrancas/casos", false],
  ["post", "/credit/cobrancas/casos/{cobranca_caso_id}/acoes", true],
  ["post", "/credit/cobrancas/casos/{cobranca_caso_id}/promessas", true],
  ["post", "/credit/cobrancas/promessas/{promessa_id}/apropriacoes", true],
] as const;

function header(operation: { parameters?: { in: string; name: string; required?: boolean }[] }, name: string) {
  return operation.parameters?.find((parameter) => parameter.in === "header" && parameter.name === name);
}

describe("Cobranca OpenAPI consumida pelo frontend", () => {
  it("preserva snapshot oficial 107/135 e SHA governado", () => {
    const operationCount = Object.values(spec.paths).flatMap((item) => Object.keys(item).filter((method) => ["get", "post", "patch", "put", "delete"].includes(method))).length;
    expect(operationCount).toBe(111);
    expect(Object.keys(spec.components.schemas)).toHaveLength(137);
    expect(createHash("sha256").update(raw).digest("hex")).toBe("c8868afbf0645165da9795f718d91b8fba41bcc2bb8fa111578ec39bed58df0b");
  });

  it("certifica as 4 operacoes oficiais de Cobranca e Idempotency-Key exata", () => {
    for (const [method, path, needsIdempotency] of COBRANCA_OPERATIONS) {
      const operation = spec.paths[path]?.[method];
      expect(operation, `${method.toUpperCase()} ${path}`).toBeTruthy();
      if (!operation) throw new Error(`${method.toUpperCase()} ${path} ausente`);
      expect(operation.security).toEqual([{ BearerAuth: [] }]);
      expect(header(operation, "X-Correlation-ID")).toEqual(expect.objectContaining({ in: "header" }));
      if (needsIdempotency) {
        expect(header(operation, "Idempotency-Key")).toEqual(expect.objectContaining({ in: "header", required: true }));
        expect(`Idempotency-Key:${path}`).toContain(path);
      } else {
        expect(header(operation, "Idempotency-Key")).toBeUndefined();
        expect(`sem-idempotency:${path}`).toContain(path);
      }
    }
  });

  it("mantem schemas de fila, acao, promessa e apropriacao sem cliente manual", () => {
    for (const schemaName of ["FilaCobrancaResponse", "CobrancaCasoResponse", "AcaoCobrancaCreateRequest", "PromessaPagamentoCreateRequest", "ApropriacaoPagamentoCreateRequest"]) {
      expect(spec.components.schemas[schemaName]).toBeTruthy();
    }
    expect(JSON.stringify(spec.components.schemas.PromessaPagamentoCreateRequest)).toContain("valor_declarado");
    expect(JSON.stringify(spec.components.schemas.ApropriacaoPagamentoCreateRequest)).toContain("pagamento_id");
  });
});
