import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

describe("contrato do bootstrap de sessao", () => {
  it("consome o snapshot governado e somente os status certificados do contexto", async () => {
    const bytes = await readFile(resolve(import.meta.dirname, "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json"));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe("ff101380ddbc11cdcd93f019c149f9819fbd7091cb42e3feb72f7e0f67189248");
    const document: unknown = JSON.parse(bytes.toString("utf8"));
    expect(isRecord(document)).toBe(true);
    if (!isRecord(document) || !isRecord(document.paths)) throw new Error("OpenAPI invalido");
    const pathItem = document.paths["/iam/contexto-atual"];
    if (!isRecord(pathItem) || !isRecord(pathItem.get) || !isRecord(pathItem.get.responses)) throw new Error("contexto ausente");
    expect(Object.keys(pathItem.get.responses).sort()).toEqual(["200", "401", "409", "500"]);
    expect(pathItem.get.requestBody).toBeUndefined();
    expect(pathItem.get.parameters).toEqual([expect.objectContaining({ in: "header", name: "X-Correlation-ID", required: false })]);
    expect(JSON.stringify(pathItem.get)).not.toMatch(/usuario_id|tenant_id|carteira_id/);
  });
});
