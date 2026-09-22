import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MercadoPagoCard } from "../../src/components/pagamentos/mercadopago.client";
import {
  INITIAL_MERCADOPAGO_ACTION_STATE,
  type MercadoPagoActionState,
  type MercadoPagoConfig,
} from "../../src/lib/pagamentos/mercadopago-policy";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }), usePathname: () => "/app/pagamentos" }));

const DESLIGADO: MercadoPagoConfig = {
  tenant_id: "tenant",
  habilitado: false,
  credencial_configurada: false,
  assinatura_configurada: false,
  testado_em: null,
  atualizado_em: "2026-09-22T12:00:00Z",
  atualizado_por: null,
};

const TESTADO: MercadoPagoConfig = {
  ...DESLIGADO,
  credencial_configurada: true,
  assinatura_configurada: true,
  testado_em: "2026-09-22T12:00:00Z",
};

function acaoQueRegistra(recebidos: FormData[], resposta: MercadoPagoConfig) {
  return async (_estado: MercadoPagoActionState, dados: FormData): Promise<MercadoPagoActionState> => {
    recebidos.push(dados);
    return { kind: "success", message: "ok", operacao: "habilitar", config: resposta, correlationId: "corr-1" };
  };
}

describe("card do recebimento por Pix", () => {
  it("mostra a taxa junto do interruptor, porque ligar custa dinheiro", () => {
    render(<MercadoPagoCard action={acaoQueRegistra([], DESLIGADO)} config={DESLIGADO} initialState={INITIAL_MERCADOPAGO_ACTION_STATE} podeConfigurar />);

    expect(screen.getByText(/0,99% por recebimento/)).toBeInTheDocument();
  });

  it("sem credencial nao oferece ligar nem testar", () => {
    render(<MercadoPagoCard action={acaoQueRegistra([], DESLIGADO)} config={DESLIGADO} initialState={INITIAL_MERCADOPAGO_ACTION_STATE} podeConfigurar />);

    expect(screen.getByRole("button", { name: "Ligar recebimento" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Testar credencial" })).toBeDisabled();
  });

  it("credencial salva mas sem teste nao deixa ligar", () => {
    const semTeste: MercadoPagoConfig = { ...TESTADO, testado_em: null };
    render(<MercadoPagoCard action={acaoQueRegistra([], semTeste)} config={semTeste} initialState={INITIAL_MERCADOPAGO_ACTION_STATE} podeConfigurar />);

    expect(screen.getByRole("button", { name: "Ligar recebimento" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Testar credencial" })).toBeEnabled();
  });

  it("testada e desligada oferece ligar, com Idempotency-Key propria", async () => {
    const recebidos: FormData[] = [];
    render(<MercadoPagoCard action={acaoQueRegistra(recebidos, { ...TESTADO, habilitado: true })} config={TESTADO} initialState={INITIAL_MERCADOPAGO_ACTION_STATE} podeConfigurar />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Ligar recebimento" }));
    });

    expect(recebidos).toHaveLength(1);
    expect(recebidos[0]?.get("intent")).toBe("habilitar");
    expect(recebidos[0]?.get("idempotency_key")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Desligar recebimento" })).toBeInTheDocument();
  });

  it("os campos de segredo sao password e nascem vazios mesmo com credencial gravada", () => {
    render(<MercadoPagoCard action={acaoQueRegistra([], TESTADO)} config={TESTADO} initialState={INITIAL_MERCADOPAGO_ACTION_STATE} podeConfigurar />);

    const token = screen.getByLabelText("Access token de producao");
    const segredo = screen.getByLabelText("Segredo do webhook");
    expect(token).toHaveAttribute("type", "password");
    expect(segredo).toHaveAttribute("type", "password");
    expect(token).toHaveValue("");
    expect(segredo).toHaveValue("");
  });

  it("sem permissao mostra o estado e esconde toda escrita", () => {
    render(<MercadoPagoCard action={acaoQueRegistra([], TESTADO)} config={TESTADO} initialState={INITIAL_MERCADOPAGO_ACTION_STATE} podeConfigurar={false} />);

    expect(screen.getByTestId("mercadopago-estado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ligar recebimento" })).toBeNull();
    expect(screen.queryByLabelText("Access token de producao")).toBeNull();
  });
});
