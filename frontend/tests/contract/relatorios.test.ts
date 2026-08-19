import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const snapshotPath = resolve("../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json");
const snapshot = JSON.parse(readFileSync(snapshotPath, "utf8")) as unknown;
const snapshotHash = createHash("sha256").update(readFileSync(snapshotPath)).digest("hex");

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function record(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) throw new Error("OpenAPI invalido");
  return value;
}

function operations() {
  const paths = record(record(snapshot).paths);
  return Object.entries(paths).flatMap(([path, methods]) =>
    Object.entries(record(methods)).map(([method, operation]) => ({ method, operation: record(operation), path })));
}

const REPORT_PATHS = [
  "/credit/carteiras/{carteira_id}/relatorios/resumo",
  "/credit/carteiras/{carteira_id}/relatorios/vencimentos",
  "/credit/carteiras/{carteira_id}/relatorios/pagamentos",
  "/credit/carteiras/{carteira_id}/relatorios/fluxo",
] as const;

describe("contrato OpenAPI de Relatorios", () => {
  it("preserva snapshot governado 106/133/SHA e os quatro GETs oficiais", () => {
    const allOperations = operations();
    const schemas = record(record(record(snapshot).components).schemas);
    expect(allOperations).toHaveLength(106);
    expect(Object.keys(schemas)).toHaveLength(133);
    expect(snapshotHash).toBe("75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34");
    for (const path of REPORT_PATHS) {
      const operation = allOperations.find((item) => item.path === path && item.method === "get");
      expect(operation, `${path} deve ser GET`).toBeTruthy();
    }
  });

  it("declara status, BearerAuth e headers sem Idempotency-Key", () => {
    for (const path of REPORT_PATHS) {
      const operation = operations().find((item) => item.path === path && item.method === "get");
      expect(operation).toBeTruthy();
      const selected = record(operation?.operation);
      expect(record(selected.responses)).toHaveProperty("200");
      expect(Object.keys(record(selected.responses)).sort()).toEqual(["200", "400", "401", "403", "404", "500"]);
      expect(JSON.stringify(selected.security)).toContain("BearerAuth");
      expect(JSON.stringify(selected.parameters)).toContain("X-Correlation-ID");
      expect(JSON.stringify(selected.parameters)).not.toContain("Idempotency-Key");
    }
  });

  it("usa somente schemas oficiais de resposta dos relatorios", () => {
    const expectedRefs = new Map([
      [REPORT_PATHS[0], "#/components/schemas/ResumoCarteiraResponse"],
      [REPORT_PATHS[1], "#/components/schemas/VencimentosInadimplenciaResponse"],
      [REPORT_PATHS[2], "#/components/schemas/PagamentosEncerramentosResponse"],
      [REPORT_PATHS[3], "#/components/schemas/FluxoPrevistoRealizadoResponse"],
    ]);
    for (const path of REPORT_PATHS) {
      const operation = operations().find((item) => item.path === path && item.method === "get");
      const response200 = record(record(record(operation?.operation).responses)["200"]);
      expect(JSON.stringify(response200)).toContain(expectedRefs.get(path));
    }
  });
});
