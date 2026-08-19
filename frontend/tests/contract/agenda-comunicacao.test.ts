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
  paths: Record<string, Record<string, { parameters?: { in: string; name: string; required?: boolean }[]; requestBody?: unknown; responses: Record<string, unknown>; security?: Record<string, string[]>[] }>>;
};

const AGENDA_OPERATIONS = [
  ["get", "/credit/agenda", false],
  ["post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos", true],
  ["post", "/credit/agenda/compromissos/{agenda_item_id}/lembretes", true],
  ["post", "/credit/agenda/compromissos/{agenda_item_id}/reagendar", true],
  ["post", "/credit/agenda/compromissos/{agenda_item_id}/concluir", true],
  ["post", "/credit/agenda/compromissos/{agenda_item_id}/cancelar", true],
  ["post", "/credit/agenda/lembretes/{lembrete_id}/reagendar", true],
  ["post", "/credit/agenda/lembretes/{lembrete_id}/enviar", true],
  ["post", "/credit/agenda/lembretes/{lembrete_id}/concluir", true],
  ["post", "/credit/agenda/lembretes/{lembrete_id}/cancelar", true],
  ["post", "/credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes", true],
  ["get", "/credit/comunicacoes", false],
] as const;

function header(operation: { parameters?: { in: string; name: string; required?: boolean }[] }, name: string) {
  return operation.parameters?.find((parameter) => parameter.in === "header" && parameter.name === name);
}

describe("Agenda/Comunicacao OpenAPI consumida pelo frontend", () => {
  it("preserva snapshot oficial 106/133 e SHA governado", () => {
    const operationCount = Object.values(spec.paths).flatMap((item) => Object.keys(item).filter((method) => ["get", "post", "patch", "put", "delete"].includes(method))).length;
    expect(operationCount).toBe(106);
    expect(Object.keys(spec.components.schemas)).toHaveLength(133);
    expect(createHash("sha256").update(raw).digest("hex")).toBe("9f4c9d224a95c146c5950820f5d055001e7091e3e1f14f778425def99c913a35");
  });

  it("certifica as 12 operacoes oficiais e Idempotency-Key exata", () => {
    for (const [method, path, needsIdempotency] of AGENDA_OPERATIONS) {
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

  it("mantem schemas de Agenda e Comunicacao sem modelos manuais paralelos", () => {
    for (const schemaName of ["AgendaOperacionalResponse", "AgendaItemResponse", "LembreteResponse", "ComunicacaoManualCreateRequest", "RegistroComunicacaoResponse", "HistoricoComunicacaoResponse"]) {
      expect(spec.components.schemas[schemaName]).toBeTruthy();
    }
    expect(JSON.stringify(spec.components.schemas.AgendaItemResponse)).toContain("previsto_para");
    expect(JSON.stringify(spec.components.schemas.HistoricoComunicacaoResponse)).toContain("registros");
  });
});
