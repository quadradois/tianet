import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MotorDetailPage, MotorPage } from "../../src/components/motor/motor";
import { INITIAL_MOTOR_ACTION_STATE, type Balance, type CalculationMemory, type InstallmentPlan, type Loan, type LoanList, type SettlementPreview } from "../../src/lib/motor/motor-policy";

const permissions = [
  "motor.emprestimo.criar",
  "motor.emprestimo.ler",
  "motor.parcela.gerar",
  "motor.parcela.ler",
  "motor.pagamento.registrar",
  "motor.saldo.ler",
  "motor.memoria.ler",
  "motor.quitacao.executar",
  "motor.renegociacao.criar",
];

const loan: Loan = {
  carteira_id: "00000000-0000-4000-8000-000000000003",
  contrato_id: "00000000-0000-4000-8000-000000000030",
  criado_em: "2026-08-14T10:00:00Z",
  devedor_id: "00000000-0000-4000-8000-000000000010",
  estado: "ativo",
  id: "00000000-0000-4000-8000-000000000040",
  moeda: "BRL",
  parametros_financeiros: { origem: "backend" },
  principal_original: "1000.00",
  tenant_id: "00000000-0000-4000-8000-000000000001",
};

const memory: CalculationMemory = {
  arredondamentos: ["backend"],
  criado_em: "2026-08-14T10:00:00Z",
  entradas: { origem: "oficial" },
  id: "00000000-0000-4000-8000-000000000050",
  passos: [{ arredondamento: null, entradas: { origem: "backend" }, nome: "passo backend", saidas: { resultado: "1000.00" } }],
  periodos: [{ referencia: "2026-08" }],
  regra: { codigo: "MOTOR" },
  resultados: { total: "1000.00" },
  tipo: "Memoria de calculo oficial",
};

const installments: InstallmentPlan = {
  emprestimo_id: loan.id,
  memoria: memory,
  parcelas: [{
    encargos: "0.00",
    emprestimo_id: loan.id,
    estado: "prevista",
    id: "00000000-0000-4000-8000-000000000060",
    juros: "10.00",
    numero: 1,
    principal: "1000.00",
    valor_liquidado: "0.00",
    valor_previsto: "1010.00",
    vencimento: "2026-09-14",
  }],
  tenant_id: loan.tenant_id,
};

const balance: Balance = {
  data_referencia: "2026-08-14",
  encargos: "0.00",
  emprestimo_id: loan.id,
  juros: "10.00",
  memoria: memory,
  principal: "1000.00",
  tenant_id: loan.tenant_id,
  total: "1010.00",
};

const settlement: SettlementPreview = {
  emprestimo_id: loan.id,
  memoria: memory,
  tenant_id: loan.tenant_id,
  valor_quitacao: { componentes: { encargos: "0.00", juros: "10.00", principal: "1000.00" }, data_referencia: "2026-08-14", moeda: "BRL", valor_total: "1010.00" },
};

async function action() {
  return INITIAL_MOTOR_ACTION_STATE;
}

describe("Motor UI", () => {
  it("renderiza estado vazio e formulario de Emprestimo sem token no browser", () => {
    const list: LoanList = { items: [], page: 1, pages: 0, size: 20, total: 0 };
    render(
      <MotorPage
        createAction={action}
        filters={{ page: 1, size: 20 }}
        initialContractId="00000000-0000-4000-8000-000000000030"
        initialState={INITIAL_MOTOR_ACTION_STATE}
        permissions={permissions}
        recoveryHref="/session/recover"
        result={{ kind: "ready", data: list }}
      />,
    );
    expect(screen.getByRole("heading", { name: /Emprestimos e pagamentos/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Contrato liberado/i)).toHaveValue("00000000-0000-4000-8000-000000000030");
    expect(screen.getByText(/empty: nenhum Emprestimo/i)).toBeInTheDocument();
    expect(screen.queryByText(/accessToken|Bearer|Authorization/i)).not.toBeInTheDocument();
  });

  it("mostra denied sem tentar fallback permissivo", () => {
    render(
      <MotorPage
        createAction={action}
        filters={{ page: 1, size: 20 }}
        initialState={INITIAL_MOTOR_ACTION_STATE}
        permissions={[]}
        recoveryHref="/session/recover"
        result={{ kind: "denied" }}
      />,
    );
    expect(screen.getAllByText("denied")[0]).toBeInTheDocument();
  });

  it("apresenta saldo, parcelas, memoria, pagamento idempotente, quitacao e renegociacao opaca", () => {
    render(
      <MotorDetailPage
        balance={{ kind: "ready", data: balance }}
        generateInstallmentsAction={action}
        initialState={INITIAL_MOTOR_ACTION_STATE}
        installments={{ kind: "ready", data: installments }}
        loan={{ kind: "ready", data: loan }}
        memories={{ kind: "ready", data: [memory] }}
        paymentAction={action}
        permissions={permissions}
        recoveryHref="/session/recover"
        renegotiationAction={action}
        settlementAction={action}
        settlementPreview={{ kind: "ready", data: settlement }}
      />,
    );
    expect(screen.getByText("Saldo oficial")).toBeInTheDocument();
    expect(screen.getAllByText("Memoria de calculo oficial")[0]).toBeInTheDocument();
    expect(screen.getByText(/Pagamento idempotente/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Quitacao oficial/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Renegociacao opaca/i)).toBeInTheDocument();
    expect(screen.getAllByText("1010.00")[0]).toBeInTheDocument();
  });

  it("mantem 404 neutro, 409, 422 e overflow observaveis", () => {
    render(
      <MotorDetailPage
        balance={{ kind: "problem", problem: { codigo: "regra_violada", correlationId: "corr-422", mensagem: "422 regra", status: 422 } }}
        generateInstallmentsAction={action}
        initialState={INITIAL_MOTOR_ACTION_STATE}
        installments={{ kind: "problem", problem: { codigo: "conflito_estado", correlationId: "corr-409", mensagem: "409 conflito", status: 409 } }}
        loan={{ kind: "problem", problem: { codigo: "recurso_indisponivel", correlationId: "corr-404", mensagem: "backend secreto", status: 404 } }}
        memories={{ kind: "denied" }}
        paymentAction={action}
        permissions={permissions}
        recoveryHref="/session/recover"
        renegotiationAction={action}
        settlementAction={action}
        settlementPreview={{ kind: "denied" }}
      />,
    );
    expect(screen.getByText(/Emprestimo nao encontrado ou indisponivel/i)).toBeInTheDocument();
  });
});
