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

const MOTOR_OPERATIONS = [
  ["post", "/credit/contratos/{contrato_id}/emprestimos", true],
  ["get", "/credit/carteiras/{carteira_id}/emprestimos", false],
  ["get", "/credit/emprestimos/{emprestimo_id}", false],
  ["post", "/credit/emprestimos/{emprestimo_id}/pagamentos", true],
  ["get", "/credit/emprestimos/{emprestimo_id}/saldo", false],
  ["get", "/credit/emprestimos/{emprestimo_id}/memoria-calculo", false],
  ["get", "/credit/emprestimos/{emprestimo_id}/quitacao", false],
  ["post", "/credit/emprestimos/{emprestimo_id}/quitacao", true],
  ["post", "/credit/emprestimos/{emprestimo_id}/renegociacoes", true],
] as const;

function header(operation: { parameters?: { in: string; name: string; required?: boolean }[] }, name: string) {
  return operation.parameters?.find((parameter) => parameter.in === "header" && parameter.name === name);
}

describe("Motor OpenAPI consumido pelo frontend", () => {
  it("preserva snapshot oficial 107/135 e SHA governado", () => {
    const operationCount = Object.values(spec.paths).flatMap((item) => Object.keys(item).filter((method) => ["get", "post", "patch", "put", "delete"].includes(method))).length;
    expect(operationCount).toBe(111);
    expect(Object.keys(spec.components.schemas)).toHaveLength(137);
    expect(createHash("sha256").update(raw).digest("hex")).toBe("95c45df44bf638233fe9d38d44398867d09d7f7b0a8a8fdc0e48c5c99597cb82");
  });

  it("certifica as 9 operacoes oficiais do Motor e Idempotency-Key exata", () => {
    for (const [method, path, needsIdempotency] of MOTOR_OPERATIONS) {
      const operation = spec.paths[path]?.[method];
      expect(operation, `${method.toUpperCase()} ${path}`).toBeTruthy();
      if (!operation) throw new Error(`${method.toUpperCase()} ${path} ausente`);
      expect(operation.security).toEqual([{ BearerAuth: [] }]);
      expect(header(operation, "X-Correlation-ID")).toEqual(expect.objectContaining({ in: "header" }));
      if (needsIdempotency) {
        expect(header(operation, "Idempotency-Key")).toEqual(expect.objectContaining({ in: "header", required: true }));
      } else {
        expect(header(operation, "Idempotency-Key")).toBeUndefined();
      }
    }
  });

  it("mantem schemas financeiros como strings e memoria governada", () => {
    for (const schemaName of ["EmprestimoResponse", "PagamentoResponse", "SaldoResponse", "MemoriaCalculoResponse", "QuitacaoResponse", "RenegociacaoResponse"]) {
      expect(spec.components.schemas[schemaName]).toBeTruthy();
    }
    expect(JSON.stringify(spec.components.schemas.SaldoResponse)).toContain("MemoriaCalculoResponse");
    expect(JSON.stringify(spec.components.schemas.PagamentoCreateRequest)).toContain("recebido_em");
    expect(JSON.stringify(spec.components.schemas.RenegociacaoCreateRequest)).toContain("novos_parametros");
  });
});
