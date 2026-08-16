import { describe, expect, it } from "vitest";

import {
  DEVEDOR_CREATE_PERMISSION,
  DEVEDOR_READ_PERMISSION,
  formBoolean,
  formString,
  hasExactPermission,
  isUuid,
  resolveDevedoresFilters,
} from "../../src/lib/devedores/devedores-policy";

describe("policy Devedores", () => {
  it("usa igualdade exata de permissao e rejeita prefixo/wildcard/perfil", () => {
    expect(hasExactPermission([DEVEDOR_READ_PERMISSION], DEVEDOR_READ_PERMISSION)).toBe(true);
    expect(hasExactPermission(["devedor.*", "devedor", "Operador"], DEVEDOR_READ_PERMISSION)).toBe(false);
    expect(hasExactPermission(["devedor.criar"], DEVEDOR_CREATE_PERMISSION)).toBe(true);
  });

  it("normaliza filtros sem aceitar tenant_id ou carteira_id", () => {
    const filters = resolveDevedoresFilters({
      carteira_id: "00000000-0000-4000-8000-000000000999",
      documento: "  123.456.789-09  ",
      estado: "ativo",
      nome: "  Maria  ",
      page: "2",
      size: "50",
      tenant_id: "tenant-hostil",
    });
    expect(filters).toEqual({ documento: "123.456.789-09", estado: "ativo", nome: "Maria", page: 2, size: 50 });
  });

  it("rejeita filtros fora do shape governado", () => {
    expect(resolveDevedoresFilters({ documento: "x".repeat(21), estado: "ativo-outra", page: "0", size: "101" })).toEqual({ page: 1, size: 20 });
    expect(isUuid("00000000-0000-4000-8000-000000000001")).toBe(true);
    expect(isUuid("devedor-livre")).toBe(false);
  });

  it("extrai campos de formulario sem criar regra financeira", () => {
    const form = new FormData();
    form.set("nome", "  Cliente  ");
    form.set("contato_preferencial", "on");
    form.set("valor_parcela", "999.99");
    expect(formString(form, "nome", 200)).toBe("Cliente");
    expect(formString(form, "valor_parcela", 3)).toBeUndefined();
    expect(formBoolean(form, "contato_preferencial")).toBe(true);
  });
});
