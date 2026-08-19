import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const currentDir = dirname(fileURLToPath(import.meta.url));
const snapshotPath = resolve(currentDir, "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json");
const raw = readFileSync(snapshotPath);
const spec = JSON.parse(raw.toString("utf8")) as {
  components: { schemas: Record<string, unknown> };
  paths: Record<string, Record<string, { parameters?: { in: string; name: string; required?: boolean }[]; responses: Record<string, unknown>; security?: Record<string, string[]>[] }>>;
};

const AUTOMACAO_OPERATIONS = [
  ["get", "/credit/automacao/jobs", false],
  ["get", "/credit/automacao/jobs/{job_id}", false],
  ["post", "/credit/automacao/jobs/{job_id}/cancelar", false],
  ["post", "/credit/automacao/jobs/{job_id}/retry", false],
  ["get", "/credit/notificacoes", false],
  ["get", "/credit/notificacoes/{notification_id}", false],
  ["get", "/credit/notificacoes/templates", false],
  ["post", "/credit/notificacoes/templates", false],
  ["post", "/credit/notificacoes/templates/{template_id}/aprovar", false],
  ["post", "/credit/notificacoes/templates/{template_id}/ativar", false],
  ["post", "/credit/notificacoes/{notification_id}/conciliar", true],
] as const;

function header(operation: { parameters?: { in: string; name: string; required?: boolean }[] }, name: string) {
  return operation.parameters?.find((parameter) => parameter.in === "header" && parameter.name === name);
}

describe("Automacao OpenAPI consumida pelo frontend", () => {
  it("preserva snapshot oficial 106/133 e SHA governado", () => {
    const operationCount = Object.values(spec.paths).flatMap((item) => Object.keys(item).filter((method) => ["get", "post", "patch", "put", "delete"].includes(method))).length;
    expect(operationCount).toBe(106);
    expect(Object.keys(spec.components.schemas)).toHaveLength(133);
    expect(createHash("sha256").update(raw).digest("hex")).toBe("9f4c9d224a95c146c5950820f5d055001e7091e3e1f14f778425def99c913a35");
  });

  it("certifica as 11 operacoes Automacao permitidas e a unica Idempotency-Key", () => {
    expect(AUTOMACAO_OPERATIONS).toHaveLength(11);
    for (const [method, path, needsIdempotency] of AUTOMACAO_OPERATIONS) {
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
    expect(spec.paths["/credit/agenda/lembretes/{lembrete_id}/enviar"]?.post).toBeTruthy();
    expect(AUTOMACAO_OPERATIONS.map(([, path]) => path)).not.toContain("/credit/agenda/lembretes/{lembrete_id}/enviar");
  });

  it("mantem schemas oficiais de jobs, notificacoes e templates", () => {
    for (const schemaName of ["JobResponse", "JobListResponse", "NotificacaoResponse", "NotificacaoListResponse", "TemplateResponse", "TemplateListResponse", "TemplateCreateRequest", "ConciliacaoRequest"]) {
      expect(spec.components.schemas[schemaName]).toBeTruthy();
    }
    expect(JSON.stringify(spec.components.schemas.EstadoJob)).toContain("falha_temporaria");
    expect(JSON.stringify(spec.components.schemas.EstadoSolicitacaoNotificacao)).toContain("resultado_desconhecido");
  });
});
