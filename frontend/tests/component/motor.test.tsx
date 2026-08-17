import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmprestimosDoDevedor, MotorDetailPage, MotorPage } from "../../src/components/motor/motor";
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
        devedores={new Map()}
        filters={{ page: 1, size: 20 }}
        initialContractId="00000000-0000-4000-8000-000000000030"
        initialState={INITIAL_MOTOR_ACTION_STATE}
        permissions={permissions}
        recoveryHref="/session/recover"
        result={{ kind: "ready", data: list }}
      />,
    );
    expect(screen.getByRole("heading", { name: /Meus emprestimos/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Contrato liberado/i)).toHaveValue("00000000-0000-4000-8000-000000000030");
    // empty: cada um dos tres grupos declara a propria ausencia, em vez de uma
    // unica mensagem generica para a pagina inteira.
    expect(screen.getByText(/Nenhum emprestimo em andamento/i)).toBeInTheDocument();
    expect(screen.getByText(/Nenhum emprestimo quitado ainda/i)).toBeInTheDocument();
    expect(screen.getByText(/Nenhum emprestimo encerrado/i)).toBeInTheDocument();
    expect(screen.queryByText(/accessToken|Bearer|Authorization/i)).not.toBeInTheDocument();
  });

  it("separa os emprestimos pelo estado devolvido, com o nome do Devedor no lugar do UUID", () => {
    const quitado: Loan = { ...loan, devedor_id: "00000000-0000-4000-8000-000000000011", estado: "quitado", id: "00000000-0000-4000-8000-000000000041" };
    const encerrado: Loan = { ...loan, devedor_id: "00000000-0000-4000-8000-000000000012", estado: "cancelado", id: "00000000-0000-4000-8000-000000000042" };
    const list: LoanList = { items: [loan, quitado, encerrado], page: 1, pages: 1, size: 20, total: 3 };
    render(
      <MotorPage
        createAction={action}
        devedores={new Map([[loan.devedor_id, "Maria Souza"], [quitado.devedor_id, "Joao Lima"]])}
        filters={{ page: 1, size: 20 }}
        initialState={INITIAL_MOTOR_ACTION_STATE}
        permissions={permissions}
        recoveryHref="/session/recover"
        result={{ kind: "ready", data: list }}
      />,
    );

    // O grupo vem do campo `estado` que o backend devolveu, nunca de uma
    // conclusao tirada de datas ou de saldo aqui.
    expect(screen.getByRole("heading", { name: /Em andamento \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Quitados \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Encerrados \(1\)/i })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Maria Souza" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Joao Lima" })).toBeInTheDocument();
    // Devedor fora do mapa degrada o rotulo; nunca cai para o identificador cru.
    expect(screen.getByRole("heading", { name: /Devedor nao identificado/i })).toBeInTheDocument();
    expect(screen.queryByText(encerrado.devedor_id)).not.toBeInTheDocument();

    expect(screen.getAllByRole("link", { name: /Mais informacoes/i })).toHaveLength(3);
  });

  it("embute os emprestimos do Devedor, omitindo grupo vazio e sem deduzir situacao", () => {
    const quitado: Loan = { ...loan, estado: "quitado", id: "00000000-0000-4000-8000-000000000043" };
    const list: LoanList = { items: [loan, quitado], page: 1, pages: 1, size: 100, total: 2 };
    render(<EmprestimosDoDevedor recoveryHref="/session/recover" result={{ kind: "ready", data: list }} />);

    expect(screen.getByRole("heading", { name: /Emprestimos deste devedor/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Em andamento \(1\)/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Quitados \(1\)/i })).toBeInTheDocument();
    // Na pagina de um Devedor especifico, grupo sem nada e ruido.
    expect(screen.queryByRole("heading", { name: /Encerrados/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Mais informacoes/i })).toHaveLength(2);
  });

  it("declara ausencia total de emprestimo do Devedor sem inventar grupo", () => {
    const list: LoanList = { items: [], page: 1, pages: 0, size: 100, total: 0 };
    render(<EmprestimosDoDevedor recoveryHref="/session/recover" result={{ kind: "ready", data: list }} />);

    expect(screen.getByText(/Este devedor ainda nao tem nenhum emprestimo/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Em andamento/i })).not.toBeInTheDocument();
  });

  it("painel responde quanto falta, qual a proxima parcela e quantas foram pagas", () => {
    const plano: InstallmentPlan = {
      ...installments,
      parcelas: [
        { ...installments.parcelas[0]!, estado: "liquidada", id: "00000000-0000-4000-8000-000000000061", numero: 1, valor_previsto: "1030.00", vencimento: "2026-09-01" },
        { ...installments.parcelas[0]!, estado: "prevista", id: "00000000-0000-4000-8000-000000000062", numero: 2, valor_previsto: "1058.06", vencimento: "2026-10-01" },
        { ...installments.parcelas[0]!, estado: "prevista", id: "00000000-0000-4000-8000-000000000063", numero: 3, valor_previsto: "1062.00", vencimento: "2026-11-01" },
      ],
    };
    render(
      <MotorDetailPage
        balance={{ kind: "ready", data: balance }}
        devedor="Maria Souza"
        generateInstallmentsAction={action}
        initialState={INITIAL_MOTOR_ACTION_STATE}
        installments={{ kind: "ready", data: plano }}
        loan={{ kind: "ready", data: loan }}
        memories={{ kind: "denied" }}
        paymentAction={action}
        permissions={permissions}
        recoveryHref="/session/recover"
        renegotiationAction={action}
        settlementAction={action}
        settlementPreview={{ kind: "denied" }}
      />,
    );

    // Quem, antes de qualquer numero.
    expect(screen.getByRole("heading", { name: "Maria Souza" })).toBeInTheDocument();
    // A proxima e a primeira ainda em aberto, nao a primeira da lista.
    // Aparece no indicador e na tabela; ambos devem dizer a mesma data.
    expect(screen.getAllByText("01/10/2026")).toHaveLength(2);
    expect(screen.getByText(/parcela 2/)).toBeInTheDocument();
    expect(screen.getByText("1 de 3")).toBeInTheDocument();
    // "liquidada" e termo de contabilidade; o Credor le "Paga".
    expect(screen.getAllByText("Paga")[0]).toBeInTheDocument();
    expect(screen.getAllByText("A vencer")[0]).toBeInTheDocument();
    expect(screen.queryByText("liquidada")).not.toBeInTheDocument();
  });

  it("nega acesso em linguagem comum, sem fallback permissivo", () => {
    render(
      <MotorPage
        createAction={action}
        devedores={new Map()}
        filters={{ page: 1, size: 20 }}
        initialState={INITIAL_MOTOR_ACTION_STATE}
        permissions={[]}
        recoveryHref="/session/recover"
        result={{ kind: "denied" }}
      />,
    );
    expect(screen.getAllByText("Sem permissao")[0]).toBeInTheDocument();
    // Nem o nome do modulo interno nem o rotulo tecnico chegam ao operador.
    expect(screen.queryByText(/denied|Modulo Motor/i)).not.toBeInTheDocument();
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
    // O painel responde as quatro perguntas antes de qualquer rolagem.
    expect(screen.getByText("Emprestado")).toBeInTheDocument();
    expect(screen.getByText("Ainda falta receber")).toBeInTheDocument();
    expect(screen.getByText("Proximo vencimento")).toBeInTheDocument();
    expect(screen.getByText("Parcelas pagas")).toBeInTheDocument();
    expect(screen.getByText("Quanto ainda falta")).toBeInTheDocument();
    expect(screen.getAllByText("Como a conta foi feita")[0]).toBeInTheDocument();
    expect(screen.getByText(/Pagamento idempotente/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Valor para quitar hoje/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Renegociacao opaca/i)).toBeInTheDocument();
    // O valor chega do backend como "1010.00" e e exibido no formato do pais.
    expect(screen.getAllByText("R$ 1.010,00")[0]).toBeInTheDocument();
    expect(screen.queryByText("1010.00")).not.toBeInTheDocument();
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
