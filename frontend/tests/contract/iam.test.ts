import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import { describe, expect, it } from "vitest";

import openapi from "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json" with { type: "json" };

const SNAPSHOT_SHA = "ff101380ddbc11cdcd93f019c149f9819fbd7091cb42e3feb72f7e0f67189248";
const IAM_OPERATIONS = [
  "GET /iam/perfis",
  "POST /iam/perfis",
  "GET /iam/perfis/{perfil_id}",
  "PATCH /iam/perfis/{perfil_id}",
  "POST /iam/perfis/{perfil_id}/inativar",
  "PUT /iam/perfis/{perfil_id}/permissoes/{codigo}",
  "DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}",
  "GET /iam/permissoes",
  "DELETE /iam/usuarios/{usuario_id}/perfil",
  "PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}",
  "GET /iam/usuarios/{usuario_id}/permissoes",
] as const;
const IDEMPOTENT_IAM = new Set([
  "POST /iam/perfis",
  "PATCH /iam/perfis/{perfil_id}",
  "POST /iam/perfis/{perfil_id}/inativar",
  "PUT /iam/perfis/{perfil_id}/permissoes/{codigo}",
  "DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}",
  "DELETE /iam/usuarios/{usuario_id}/perfil",
  "PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}",
]);
const IDEMPOTENCY_MARKERS = [
  "Idempotency-Key:POST /iam/perfis",
  "Idempotency-Key:PATCH /iam/perfis/{perfil_id}",
  "Idempotency-Key:POST /iam/perfis/{perfil_id}/inativar",
  "Idempotency-Key:PUT /iam/perfis/{perfil_id}/permissoes/{codigo}",
  "Idempotency-Key:DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}",
  "Idempotency-Key:DELETE /iam/usuarios/{usuario_id}/perfil",
  "Idempotency-Key:PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}",
] as const;
const SEM_IDEMPOTENCY_MARKERS = [
  "sem-idempotency:GET /iam/perfis",
  "sem-idempotency:GET /iam/perfis/{perfil_id}",
  "sem-idempotency:GET /iam/permissoes",
  "sem-idempotency:GET /iam/usuarios/{usuario_id}/permissoes",
] as const;

type OpenApiParameter = Readonly<{ in?: string; name?: string }>;
type OpenApiOperation = Readonly<{ parameters?: readonly OpenApiParameter[]; responses?: Record<string, unknown>; security?: unknown }>;

function operationEntries(): [string, OpenApiOperation][] {
  const result: [string, OpenApiOperation][] = [];
  for (const [route, pathItem] of Object.entries(openapi.paths)) {
    for (const [method, operation] of Object.entries(pathItem)) result.push([`${method.toUpperCase()} ${route}`, operation as OpenApiOperation]);
  }
  return result;
}

describe("contrato OpenAPI IAM permitido", () => {
  it("preserva snapshot 106/133 e hash oficial", async () => {
    const bytes = await readFile(new URL("../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json", import.meta.url));
    expect(createHash("sha256").update(bytes).digest("hex")).toBe(SNAPSHOT_SHA);
    expect(operationEntries()).toHaveLength(106);
    expect(Object.keys(openapi.components.schemas)).toHaveLength(133);
  });

  it("certifica exatamente 11 operacoes IAM permitidas sem credenciais ou lista de Usuarios", () => {
    const iam = operationEntries().filter(([operation]) => operation.includes("/iam/") && !operation.includes("/iam/contexto-atual"));
    expect(iam.map(([operation]) => operation).filter((operation) => IAM_OPERATIONS.includes(operation as typeof IAM_OPERATIONS[number])).sort()).toEqual([...IAM_OPERATIONS].sort());
    expect(iam.map(([operation]) => operation)).toContain("PATCH /iam/credencial");
    expect([...IAM_OPERATIONS]).not.toContain("PATCH /iam/credencial");
    expect([...IAM_OPERATIONS].some((operation) => operation.includes("credencial"))).toBe(false);
    expect([...IAM_OPERATIONS as readonly string[]].some((operation) => operation === "GET /iam/usuarios")).toBe(false);
  });

  it("mantem Bearer, X-Correlation-ID e Idempotency-Key apenas nos comandos certificados", () => {
    expect(IDEMPOTENCY_MARKERS).toHaveLength(7);
    expect(SEM_IDEMPOTENCY_MARKERS).toHaveLength(4);
    for (const [name, operation] of operationEntries().filter(([operation]) => IAM_OPERATIONS.includes(operation as typeof IAM_OPERATIONS[number]))) {
      expect(operation.security).toEqual([{ BearerAuth: [] }]);
      const headers = operation.parameters?.filter((parameter) => parameter.in === "header").map((parameter) => parameter.name) ?? [];
      expect(headers).toContain("X-Correlation-ID");
      if (IDEMPOTENT_IAM.has(name)) expect(headers).toContain("Idempotency-Key");
      else expect(headers).not.toContain("Idempotency-Key");
    }
  });

  it("usa schemas oficiais de Perfil, Catalogo e Permissoes efetivas", () => {
    expect(openapi.components.schemas.PerfilResponse.required.toSorted()).toEqual(["estado", "id", "nome", "permissoes", "tenant_id"].toSorted());
    expect(openapi.components.schemas.PermissoesCatalogoResponse.required.toSorted()).toEqual(["itens", "versao"].toSorted());
    expect(openapi.components.schemas.PermissoesEfetivasResponse.required.toSorted()).toEqual(["perfil_id", "perfil_nome", "permissoes", "usuario_id"].toSorted());
  });
});
