import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const HTTP_METHODS = new Set(["get", "post", "put", "patch", "delete"]);
const snapshotUrl = new URL(
  "../../../docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json",
  import.meta.url,
);

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new TypeError("Expected an OpenAPI object");
  }
  return value;
}

describe("certified OpenAPI snapshot", () => {
  it("observa o inventario e os contratos certificados sem gerar cliente", async () => {
    const raw = await readFile(fileURLToPath(snapshotUrl), "utf8");
    const parsed: unknown = JSON.parse(raw);
    const snapshot = asRecord(parsed);
    const paths = asRecord(snapshot.paths);
    const components = asRecord(snapshot.components);
    const schemas = asRecord(components.schemas);
    const operationCount = Object.values(paths).reduce<number>((total, pathItem) => {
      const methods = Object.keys(asRecord(pathItem)).filter((method) => HTTP_METHODS.has(method));
      return total + methods.length;
    }, 0);

    expect(operationCount).toBe(108);
    expect(Object.keys(schemas)).toHaveLength(137);
    expect(asRecord(paths["/health"])).toHaveProperty("get");
    expect(asRecord(paths["/iam/contexto-atual"])).toHaveProperty("get");
    expect(asRecord(paths["/iam/permissoes"])).toHaveProperty("get");
  });
});
