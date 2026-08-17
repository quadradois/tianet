import { describe, expect, it } from "vitest";

import {
  normalizarDecimal,
  permissoesFaltantes,
  podeLancar,
  validarCondicoes,
  validarDevedor,
} from "../../src/lib/lancamento/lancamento-policy";

const TODAS = [
  "devedor.criar",
  "comercial.proposta.criar",
  "contratos.contrato.criar",
  "motor.emprestimo.criar",
];

const CONDICOES_OK = {
  valor: "6000.00",
  taxa: "0.0300",
  parcelas: "3",
  primeiroVencimento: "2026-09-20",
};

describe("lancamento-policy", () => {
  it("exige as quatro permissoes da cadeia, nao uma bastando por todas", () => {
    expect(podeLancar(TODAS)).toBe(true);
    for (const ausente of TODAS) {
      const parciais = TODAS.filter((p) => p !== ausente);
      expect(podeLancar(parciais)).toBe(false);
      expect(permissoesFaltantes(parciais)).toEqual([ausente]);
    }
  });

  it("valida a forma das condicoes sem calcular nada", () => {
    expect(validarCondicoes(CONDICOES_OK)).toEqual([]);
    expect(validarCondicoes({ ...CONDICOES_OK, valor: "6.000,00" })).toHaveLength(1);
    expect(validarCondicoes({ ...CONDICOES_OK, parcelas: "0" })).toHaveLength(1);
    expect(validarCondicoes({ ...CONDICOES_OK, parcelas: "2.5" })).toHaveLength(1);
    expect(validarCondicoes({ ...CONDICOES_OK, parcelas: "361" })).toHaveLength(1);
    expect(validarCondicoes({ ...CONDICOES_OK, primeiroVencimento: "20/09/2026" })).toHaveLength(1);
    expect(validarCondicoes({ valor: "", taxa: "", parcelas: "", primeiroVencimento: "" })).toHaveLength(4);
  });

  it("aceita virgula decimal e entrega ponto ao contrato", () => {
    expect(validarCondicoes({ ...CONDICOES_OK, valor: "1234,56" })).toEqual([]);
    expect(normalizarDecimal("1234,56")).toBe("1234.56");
    expect(normalizarDecimal(" 1234.56 ")).toBe("1234.56");
  });

  it("aceita devedor existente por UUID e recusa identificador invalido", () => {
    expect(validarDevedor({ devedorId: "072b595f-0749-41c5-93a8-00c258e6c613" })).toEqual([]);
    expect(validarDevedor({ devedorId: "nao-e-uuid" })).toHaveLength(1);
  });

  it("exige WhatsApp ao cadastrar devedor novo, porque o comprovante precisa de destino", () => {
    const completo = { documento: "52998224725", nome: "Cliente", contatoWhatsapp: "(11) 98888-7766" };
    expect(validarDevedor(completo)).toEqual([]);
    expect(validarDevedor({ ...completo, contatoWhatsapp: "" })).toEqual([
      "Informe o WhatsApp do devedor.",
    ]);
    expect(validarDevedor({})).toHaveLength(3);
  });
});
