import { describe, expect, it } from "vitest";

function normalizeHarnessSegments(segments: readonly string[]): string {
  return segments.map((segment) => segment.trim()).filter(Boolean).join(":");
}

describe("unit harness", () => {
  it("executa uma funcao tecnica pura com resultado deterministico", () => {
    expect(normalizeHarnessSegments([" frontend ", "", " unit "])).toBe("frontend:unit");
  });
});
