import { describe, expect, it } from "vitest";

import {
  hasAnyIamPermission,
  hasExactIamPermission,
  isPermissionCode,
  resolveIamFilters,
} from "../../src/lib/iam/iam-policy";

describe("politica IAM permitida", () => {
  it("usa igualdade exata de permissao e rejeita prefixos", () => {
    expect(hasExactIamPermission(["perfil.ler"], "perfil.ler")).toBe(true);
    expect(hasExactIamPermission(["perfil.*"], "perfil.ler")).toBe(false);
    expect(hasAnyIamPermission(["perfil.gerir"])).toBe(true);
    expect(hasAnyIamPermission(["perfil"])).toBe(false);
  });

  it("aceita somente codigos de permissao canonicos", () => {
    expect(isPermissionCode("perfil.ler")).toBe(true);
    expect(isPermissionCode("tenant.usuario.gerir")).toBe(true);
    expect(isPermissionCode("Perfil.Ler")).toBe(false);
    expect(isPermissionCode("perfil")).toBe(false);
  });

  it("normaliza somente UUIDs de Perfil e Usuario conhecido", () => {
    const filters = resolveIamFilters({
      perfil_id: "00000000-0000-4000-8000-000000000010",
      tenant_id: "hostil",
      usuario_id: "00000000-0000-4000-8000-000000000011",
    });
    expect(filters).toEqual({
      perfilId: "00000000-0000-4000-8000-000000000010",
      usuarioId: "00000000-0000-4000-8000-000000000011",
    });
    expect(resolveIamFilters({ perfil_id: "perfil.ler", usuario_id: "usuario" })).toEqual({});
  });
});
