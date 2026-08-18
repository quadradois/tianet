import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import { describe, expect, expectTypeOf, it } from "vitest";

import type { components, paths } from "../../src/lib/api/openapi.generated";

const HTTP_METHODS = new Set(["get", "post", "put", "patch", "delete"]);
const ERROR_STATUSES = new Set(["400", "401", "403", "404", "409", "422", "500", "503"]);
const SNAPSHOT_SHA256 = "ba4342af3a977fe65e0f0af60d7e6fd7cab219b386a4f9c03b9167051a1c02cd";
const snapshotUrl = new URL(
  "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json",
  import.meta.url,
);

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) throw new TypeError("Expected an OpenAPI object");
  return value;
}

function responseSchema(response: unknown): unknown {
  const content = asRecord(asRecord(response).content);
  return asRecord(content["application/json"]).schema;
}

describe("generated OpenAPI client contract", () => {
  it("deriva auth, contexto, catalogo e erro apenas dos tipos gerados", () => {
    type LoginBody = paths["/auth/login"]["post"]["requestBody"]["content"]["application/json"];
    type RefreshBody = paths["/auth/refresh"]["post"]["requestBody"]["content"]["application/json"];
    type LogoutBody = paths["/auth/logout"]["post"]["requestBody"]["content"]["application/json"];
    type ContextResponse = paths["/iam/contexto-atual"]["get"]["responses"][200]["content"]["application/json"];
    type CatalogResponse = paths["/iam/permissoes"]["get"]["responses"][200]["content"]["application/json"];
    type IdempotentHeaders = paths["/credit/carteiras/{carteira_id}/devedores"]["post"]["parameters"]["header"];

    expectTypeOf<LoginBody>().toEqualTypeOf<components["schemas"]["AuthLoginRequest"]>();
    expectTypeOf<RefreshBody>().toEqualTypeOf<components["schemas"]["AuthRefreshRequest"]>();
    expectTypeOf<LogoutBody>().toEqualTypeOf<components["schemas"]["AuthRefreshRequest"]>();
    expectTypeOf<ContextResponse>().toEqualTypeOf<components["schemas"]["ContextoOperacionalResponse"]>();
    expectTypeOf<CatalogResponse>().toEqualTypeOf<components["schemas"]["PermissoesCatalogoResponse"]>();
    expectTypeOf<components["schemas"]["ErroResponse"]>().toMatchObjectType<{
      readonly codigo: string;
      readonly mensagem: string;
    }>();
    expectTypeOf<{ readonly email: string }>().not.toExtend<LoginBody>();
    expectTypeOf<{ readonly Payload: string }>().not.toExtend<RefreshBody>();
    expectTypeOf<{ readonly "X-Correlation-ID"?: string }>().not.toExtend<IdempotentHeaders>();
  });

  it("observa snapshot imutavel, idempotencia required e envelopes de erro", async () => {
    const raw = await readFile(snapshotUrl);
    expect(createHash("sha256").update(raw).digest("hex")).toBe(SNAPSHOT_SHA256);
    const parsed: unknown = JSON.parse(raw.toString("utf8"));
    const snapshot = asRecord(parsed);
    const pathsObject = asRecord(snapshot.paths);
    const schemas = asRecord(asRecord(snapshot.components).schemas);
    let operationCount = 0;
    const idempotencyParameters: Array<Record<string, unknown>> = [];

    for (const pathItem of Object.values(pathsObject)) {
      for (const [method, operationValue] of Object.entries(asRecord(pathItem))) {
        if (!HTTP_METHODS.has(method)) continue;
        operationCount += 1;
        const operation = asRecord(operationValue);
        const parameters = Array.isArray(operation.parameters) ? operation.parameters : [];
        for (const parameterValue of parameters) {
          const parameter = asRecord(parameterValue);
          if (parameter.in === "header" && parameter.name === "Idempotency-Key") {
            idempotencyParameters.push(parameter);
          }
        }

        const responses = asRecord(operation.responses);
        for (const [status, response] of Object.entries(responses)) {
          if (!ERROR_STATUSES.has(status)) continue;
          const schema = responseSchema(response);
          const expected = status === "503" ? "#/components/schemas/HealthResponse" : "#/components/schemas/ErroResponse";
          expect(schema).toEqual({ $ref: expected });
        }
      }
    }

    expect(operationCount).toBe(108);
    expect(Object.keys(schemas)).toHaveLength(137);
    expect(idempotencyParameters).toHaveLength(31);
    for (const parameter of idempotencyParameters) {
      expect(parameter.required).toBe(true);
      expect(asRecord(parameter.schema)).toMatchObject({ minLength: 1, maxLength: 255 });
    }

    const loginBody = asRecord(asRecord(asRecord(pathsObject["/auth/login"]).post).requestBody);
    expect(asRecord(asRecord(loginBody.content)["application/json"]).schema).toEqual({
      $ref: "#/components/schemas/AuthLoginRequest",
    });
    for (const path of ["/auth/refresh", "/auth/logout"]) {
      const body = asRecord(asRecord(asRecord(pathsObject[path]).post).requestBody);
      expect(asRecord(asRecord(body.content)["application/json"]).schema).toEqual({
        $ref: "#/components/schemas/AuthRefreshRequest",
      });
    }
    expect(pathsObject).toHaveProperty("/iam/contexto-atual");
    expect(pathsObject).toHaveProperty("/iam/permissoes");
  });
});
