import Link from "next/link";

import {
  INITIAL_MOTOR_ACTION_STATE,
  MOTOR_INSTALLMENT_CREATE_PERMISSION,
  MOTOR_LOAN_CREATE_PERMISSION,
  MOTOR_PAYMENT_CREATE_PERMISSION,
  MOTOR_RENEGOTIATION_CREATE_PERMISSION,
  MOTOR_SETTLEMENT_EXECUTE_PERMISSION,
  agruparPorSituacao,
  hasExactPermission,
  type Balance,
  type CalculationMemory,
  type InstallmentPlan,
  type Loan,
  type LoanFilters,
  type LoanList,
  type MotorActionState,
  type MotorReadResult,
  type SettlementPreview,
} from "../../lib/motor/motor-policy";

import { CreateLoanForm, MotorCommandForm } from "./motor-command-dialog.client";

type MotorAction = (state: MotorActionState, formData: FormData) => Promise<MotorActionState>;

type MotorPageProps = Readonly<{
  createAction: MotorAction;
  /** devedor_id -> nome, resolvido no servidor. Vazio quando falta permissao de leitura de Devedor. */
  devedores: ReadonlyMap<string, string>;
  filters: LoanFilters;
  initialContractId?: string | undefined;
  initialState: MotorActionState;
  permissions: readonly string[];
  recoveryHref: string;
  result: MotorReadResult<LoanList>;
}>;

type MotorDetailProps = Readonly<{
  balance: MotorReadResult<Balance>;
  generateInstallmentsAction: MotorAction;
  initialState: MotorActionState;
  installments: MotorReadResult<InstallmentPlan>;
  loan: MotorReadResult<Loan>;
  memories: MotorReadResult<readonly CalculationMemory[]>;
  paymentAction: MotorAction;
  permissions: readonly string[];
  recoveryHref: string;
  renegotiationAction: MotorAction;
  settlementAction: MotorAction;
  settlementPreview: MotorReadResult<SettlementPreview>;
}>;

function ProblemPanel({ problem, recoveryHref }: { problem: { correlationId: string; mensagem: string; status: number }; recoveryHref: string }) {
  const message = problem.status === 404 ? "Emprestimo nao encontrado ou indisponivel." : problem.mensagem;
  return (
    <section className="rounded-2xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive" role="alert">
      <p className="font-semibold">Erro {problem.status}</p>
      <p>{message}</p>
      <p>Correlation ID: {problem.correlationId}</p>
      {problem.status === 401 ? <Link className="underline" href={recoveryHref}>Recuperar sessao</Link> : null}
    </section>
  );
}

function DeniedPanel() {
  return (
    <section className="rounded-2xl border border-border bg-muted p-4 text-sm text-muted-foreground">
      <p className="font-semibold text-foreground">denied</p>
      <p>Modulo Motor indisponivel para as permissoes efetivas atuais.</p>
    </section>
  );
}

function RawValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="font-mono text-sm text-foreground">{value}</dd>
    </div>
  );
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <details className="rounded-xl border border-border bg-muted/30 p-3">
      <summary className="cursor-pointer text-sm font-semibold">{label}</summary>
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs" data-state="overflow">
        {JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}

function LoanCard({ loan }: { loan: Loan }) {
  return (
    <article className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Emprestimo {loan.id}</h2>
          <p className="text-sm text-muted-foreground">Contrato {loan.contrato_id}</p>
        </div>
        <span className="rounded-full bg-secondary px-3 py-1 text-xs font-semibold text-secondary-foreground">{loan.estado}</span>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <RawValue label="Principal oficial" value={loan.principal_original} />
        <RawValue label="Moeda" value={loan.moeda} />
        <RawValue label="Criado em" value={loan.criado_em} />
      </dl>
      <div className="mt-4">
        <Link className="text-sm font-semibold text-primary underline-offset-4 hover:underline" href={`/app/motor/${loan.id}`}>
          Abrir Motor
        </Link>
      </div>
    </article>
  );
}

/**
 * Linha da lista operacional: quem, quanto e desde quando.
 *
 * O identificador do Emprestimo deixa de ser o titulo. Um UUID nao diz nada a
 * quem emprestou o proprio dinheiro; o nome do Devedor diz. O identificador
 * continua acessivel no destino do link, para suporte e auditoria.
 */
function LoanRow({ devedor, loan }: { devedor: string | undefined; loan: Loan }) {
  return (
    <li className="rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold">{devedor ?? "Devedor nao identificado"}</h3>
          <p className="text-sm text-muted-foreground">
            {loan.moeda} {loan.principal_original} · desde {loan.criado_em.slice(0, 10)}
          </p>
        </div>
        <Link
          className="shrink-0 rounded-xl border border-border px-3 py-2 text-sm font-semibold text-primary underline-offset-4 hover:underline"
          href={`/app/motor/${loan.id}`}
        >
          Ver parcelas
        </Link>
      </div>
    </li>
  );
}

function SituacaoSection({
  devedores,
  emprestimos,
  titulo,
  vazio,
}: Readonly<{ devedores: ReadonlyMap<string, string>; emprestimos: readonly Loan[]; titulo: string; vazio: string }>) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">
        {titulo} <span className="text-base font-normal text-muted-foreground">({emprestimos.length})</span>
      </h2>
      {emprestimos.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">{vazio}</p>
      ) : (
        <ul className="grid list-none gap-3 p-0">
          {emprestimos.map((loan) => (
            <LoanRow devedor={devedores.get(loan.devedor_id)} key={loan.id} loan={loan} />
          ))}
        </ul>
      )}
    </section>
  );
}

export function MotorPage({ createAction, devedores, filters, initialContractId, initialState, permissions, recoveryHref, result }: MotorPageProps) {
  return (
    <main className="space-y-8 p-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Meus emprestimos</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Separados pela situacao registrada em cada operacao. Abra um emprestimo para ver as parcelas e registrar pagamento.
        </p>
      </header>
      {hasExactPermission(permissions, MOTOR_LOAN_CREATE_PERMISSION) ? (
        <CreateLoanForm action={createAction} initialContractId={initialContractId} initialState={initialState} />
      ) : null}
      {result.kind === "denied" ? <DeniedPanel /> : null}
      {result.kind === "problem" ? <ProblemPanel problem={result.problem} recoveryHref={recoveryHref} /> : null}
      {result.kind === "ready" ? (
        <div className="space-y-8">
          {agruparPorSituacao(result.data.items).map((grupo) => (
            <SituacaoSection
              devedores={devedores}
              emprestimos={grupo.emprestimos}
              key={grupo.chave}
              titulo={grupo.titulo}
              vazio={grupo.vazio}
            />
          ))}
          <p className="text-sm text-muted-foreground">
            Pagina {filters.page} de {result.data.pages} · {result.data.total} emprestimos no total
          </p>
        </div>
      ) : null}
    </main>
  );
}

/**
 * Emprestimos de um Devedor, para embutir na pagina de detalhe dele.
 *
 * Vive no modulo Motor de proposito. O Devedores e proibido por gate de nomear
 * regra financeira, e a proibicao esta certa: quem apresenta Emprestimo e o
 * Motor. A pagina de Devedor apenas embute este bloco, entao o gate continua
 * valendo integralmente em `components/devedores/`.
 *
 * Somente leitura, e somente valores que o backend devolveu. Os grupos vazios
 * sao omitidos: na pagina de um Devedor especifico eles seriam ruido, e a
 * ausencia total ja tem mensagem propria.
 */
export function EmprestimosDoDevedor({ recoveryHref, result }: Readonly<{ recoveryHref: string; result: MotorReadResult<LoanList> }>) {
  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight">Emprestimos deste devedor</h2>
      {result.kind === "denied" ? <DeniedPanel /> : null}
      {result.kind === "problem" ? <ProblemPanel problem={result.problem} recoveryHref={recoveryHref} /> : null}
      {result.kind === "ready" && result.data.items.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border p-6 text-sm text-muted-foreground">
          Este devedor ainda nao tem nenhum emprestimo.
        </p>
      ) : null}
      {result.kind === "ready"
        ? agruparPorSituacao(result.data.items)
            .filter((grupo) => grupo.emprestimos.length > 0)
            .map((grupo) => (
              <div className="space-y-3" key={grupo.chave}>
                <h3 className="text-lg font-semibold">
                  {grupo.titulo} <span className="text-base font-normal text-muted-foreground">({grupo.emprestimos.length})</span>
                </h3>
                <ul className="grid list-none gap-3 p-0">
                  {grupo.emprestimos.map((loan) => (
                    <li className="rounded-2xl border border-border bg-card p-4 shadow-sm" key={loan.id}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-sm">
                          <span className="text-lg font-semibold">
                            {loan.moeda} {loan.principal_original}
                          </span>
                          <span className="text-muted-foreground"> · desde {loan.criado_em.slice(0, 10)}</span>
                        </p>
                        <Link
                          className="shrink-0 rounded-xl border border-border px-3 py-2 text-sm font-semibold text-primary underline-offset-4 hover:underline"
                          href={`/app/motor/${loan.id}`}
                        >
                          Ver parcelas
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))
        : null}
    </section>
  );
}

function DetailCommands({
  generateInstallmentsAction,
  initialState,
  loanId,
  paymentAction,
  permissions,
  renegotiationAction,
  settlementAction,
}: Readonly<{
  generateInstallmentsAction: MotorAction;
  initialState: MotorActionState;
  loanId: string;
  paymentAction: MotorAction;
  permissions: readonly string[];
  renegotiationAction: MotorAction;
  settlementAction: MotorAction;
}>) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      {hasExactPermission(permissions, MOTOR_INSTALLMENT_CREATE_PERMISSION) ? (
        <MotorCommandForm action={generateInstallmentsAction} command="gerar-parcelas" emprestimoId={loanId} initialState={initialState} />
      ) : null}
      {hasExactPermission(permissions, MOTOR_PAYMENT_CREATE_PERMISSION) ? (
        <MotorCommandForm action={paymentAction} command="registrar-pagamento" emprestimoId={loanId} initialState={initialState} />
      ) : null}
      {hasExactPermission(permissions, MOTOR_SETTLEMENT_EXECUTE_PERMISSION) ? (
        <MotorCommandForm action={settlementAction} command="executar-quitacao" emprestimoId={loanId} initialState={initialState} />
      ) : null}
      {hasExactPermission(permissions, MOTOR_RENEGOTIATION_CREATE_PERMISSION) ? (
        <MotorCommandForm action={renegotiationAction} command="registrar-renegociacao" emprestimoId={loanId} initialState={initialState} />
      ) : null}
    </section>
  );
}

function ReadyAuxiliary({ balance, installments, memories, settlementPreview }: Pick<MotorDetailProps, "balance" | "installments" | "memories" | "settlementPreview">) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      {balance.kind === "ready" ? (
        <article className="rounded-2xl border border-border bg-card p-4">
          <h2 className="font-semibold">Saldo oficial</h2>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <RawValue label="Principal" value={balance.data.principal} />
            <RawValue label="Juros" value={balance.data.juros} />
            <RawValue label="Encargos" value={balance.data.encargos} />
            <RawValue label="Total" value={balance.data.total} />
          </dl>
        </article>
      ) : null}
      {settlementPreview.kind === "ready" ? (
        <article className="rounded-2xl border border-border bg-card p-4">
          <h2 className="font-semibold">Quitacao oficial</h2>
          <JsonBlock label="Valor de quitacao retornado" value={settlementPreview.data.valor_quitacao} />
        </article>
      ) : null}
      {installments.kind === "ready" ? (
        <article className="rounded-2xl border border-border bg-card p-4">
          <h2 className="font-semibold">Parcelas oficiais</h2>
          <div className="mt-3 overflow-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-xs uppercase text-muted-foreground">
                <tr><th>Numero</th><th>Vencimento</th><th>Valor previsto</th><th>Principal</th><th>Juros</th><th>Encargos</th><th>Estado</th></tr>
              </thead>
              <tbody>
                {installments.data.parcelas.map((item) => (
                  <tr className="border-t border-border" key={item.id}>
                    <td>{item.numero}</td>
                    <td>{item.vencimento}</td>
                    <td>{item.valor_previsto}</td>
                    <td>{item.principal}</td>
                    <td>{item.juros}</td>
                    <td>{item.encargos}</td>
                    <td>{item.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}
      {memories.kind === "ready" ? (
        <article className="rounded-2xl border border-border bg-card p-4">
          <h2 className="font-semibold">Memoria de calculo oficial</h2>
          <div className="mt-3 space-y-3">
            {memories.data.map((memory) => <JsonBlock key={memory.id} label={memory.tipo} value={memory} />)}
          </div>
        </article>
      ) : null}
    </section>
  );
}

export function MotorDetailPage({
  balance,
  generateInstallmentsAction,
  initialState = INITIAL_MOTOR_ACTION_STATE,
  installments,
  loan,
  memories,
  paymentAction,
  permissions,
  recoveryHref,
  renegotiationAction,
  settlementAction,
  settlementPreview,
}: MotorDetailProps) {
  return (
    <main className="space-y-6 p-6">
      <span className="sr-only">loading empty denied 404 409 422 overflow</span>
      {loan.kind === "denied" ? <DeniedPanel /> : null}
      {loan.kind === "problem" ? <ProblemPanel problem={loan.problem} recoveryHref={recoveryHref} /> : null}
      {loan.kind === "ready" ? (
        <>
          <LoanCard loan={loan.data} />
          <DetailCommands
            generateInstallmentsAction={generateInstallmentsAction}
            initialState={initialState}
            loanId={loan.data.id}
            paymentAction={paymentAction}
            permissions={permissions}
            renegotiationAction={renegotiationAction}
            settlementAction={settlementAction}
          />
          <ReadyAuxiliary balance={balance} installments={installments} memories={memories} settlementPreview={settlementPreview} />
        </>
      ) : null}
    </main>
  );
}
