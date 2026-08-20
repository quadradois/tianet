import { describe, expect, it } from "vitest";

import { cpf, data, mascaraMoeda, moeda, normalizarMoeda } from "../../src/lib/formato/brasileiro";

describe("formatacao brasileira", () => {
  it("formata dinheiro agrupando milhares sem converter para numero", () => {
    expect(moeda("10000.00")).toBe("R$ 10.000,00");
    expect(moeda("0.00")).toBe("R$ 0,00");
    expect(moeda("1058.06")).toBe("R$ 1.058,06");
    expect(moeda("999.99")).toBe("R$ 999,99");
    expect(moeda("1000.00")).toBe("R$ 1.000,00");
    expect(moeda("1234567890.12")).toBe("R$ 1.234.567.890,12");
    expect(moeda("-250.50")).toBe("-R$ 250,50");
  });

  it("completa centavos ausentes sem arredondar", () => {
    expect(moeda("10")).toBe("R$ 10,00");
    expect(moeda("10.5")).toBe("R$ 10,50");
    // Precisao extra e truncada na exibicao, nunca somada nem arredondada: o
    // backend continua sendo a autoridade sobre o valor.
    expect(moeda("10.567")).toBe("R$ 10,56");
  });

  it("devolve o valor cru quando nao reconhece a forma", () => {
    // Exibir o dado como veio e preferivel a exibir um numero inventado.
    expect(moeda("indisponivel")).toBe("indisponivel");
    expect(moeda(undefined)).toBe("");
    expect(moeda(null)).toBe("");
  });

  it("normaliza dinheiro digitado em BRL para o contrato sem usar ponto flutuante", () => {
    expect(normalizarMoeda("2.000")).toBe("2000.00");
    expect(normalizarMoeda("2.000,00")).toBe("2000.00");
    expect(normalizarMoeda("R$ 2.000,50")).toBe("2000.50");
    expect(normalizarMoeda("2000,5")).toBe("2000.50");
    expect(normalizarMoeda("2000")).toBe("2000.00");
    expect(normalizarMoeda("2000.00")).toBeUndefined();
  });

  it("mascara entrada monetaria reconhecida em BRL", () => {
    expect(mascaraMoeda("2.000")).toBe("R$ 2.000,00");
    expect(mascaraMoeda("2000,50")).toBe("R$ 2.000,50");
    expect(mascaraMoeda("abc")).toBe("abc");
  });

  it("formata CPF e preserva entrada que nao seja CPF", () => {
    expect(cpf("39053344705")).toBe("390.533.447-05");
    expect(cpf("390.533.447-05")).toBe("390.533.447-05");
    expect(cpf("123")).toBe("123");
    expect(cpf(undefined)).toBe("");
  });

  it("formata data sem construir Date, para nao deslocar o dia por fuso", () => {
    expect(data("2026-08-17")).toBe("17/08/2026");
    expect(data("2026-08-17T18:32:00.325592Z")).toBe("17/08/2026");
    // 00:00Z deslocaria para o dia anterior em America/Sao_Paulo se passasse
    // por `new Date`. A leitura textual protege o vencimento.
    expect(data("2026-01-01T00:00:00Z")).toBe("01/01/2026");
    expect(data("sem data")).toBe("sem data");
    expect(data(undefined)).toBe("");
  });
});
