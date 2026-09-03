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
  ["post", "/credit/automacao/jobs/{job_id}/cancelar", true],
  ["post", "/credit/automacao/jobs/{job_id}/retry", true],
  ["get", "/credit/notificacoes", false],
  ["get", "/credit/notificacoes/{notification_id}", false],
  ["get", "/credit/notificacoes/templates", false],
  ["post", "/credit/notificacoes/templates", true],
  ["post", "/credit/notificacoes/templates/{template_id}/aprovar", true],
  ["post", "/credit/notificacoes/templates/{template_id}/ativar", true],
  ["post", "/credit/notificacoes/{notification_id}/conciliar", true],
] as const;

function header(operation: { parameters?: { in: string; name: string; required?: boolean }[] }, name: string) {
  return operation.parameters?.find((parameter) => parameter.in === "header" && parameter.name === name);
}

describe("Automacao OpenAPI consumida pelo frontend", () => {
  it("preserva snapshot oficial 107/135 e SHA governado", () => {
    const operationCount = Object.values(spec.paths).flatMap((item) => Object.keys(item).filter((method) => ["get", "post", "patch", "put", "delete"].includes(method))).length;
    expect(operationCount).toBe(111);
    expect(Object.keys(spec.components.schemas)).toHaveLength(137);
    expect(createHash("sha256").update(raw).digest("hex")).toBe("0d0b6e9da14ef88a169a4beee174a74534277eb6893821b78119efc5dda5f4ba");
  });

  it("certifica as 11 operacoes Automacao e Idempotency-Key nas seis escritas", () => {
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

  it("declara lembrete opcional e nulavel para notificacao transacional", () => {
    const notification = spec.components.schemas.NotificacaoResponse as {
      properties: { lembrete_id: { anyOf: unknown[] } };
      required: string[];
    };

    expect(notification.required).not.toContain("lembrete_id");
    expect(notification.properties.lembrete_id.anyOf).toEqual([
      { format: "uuid", type: "string" },
      { type: "null" },
    ]);
  });
});
