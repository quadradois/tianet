import Link from "next/link";

import { data as formatarData, moeda } from "../../lib/formato/brasileiro";
import { Button } from "../ui/button";
import { Sheet, SheetBody, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "../ui/sheet";

import {
  INITIAL_MOTOR_ACTION_STATE,
  MOTOR_LOAN_CREATE_PERMISSION,
  MOTOR_PAYMENT_CREATE_PERMISSION,
  MOTOR_RENEGOTIATION_CREATE_PERMISSION,
  MOTOR_SETTLEMENT_EXECUTE_PERMISSION,
  SITUACOES,
  agruparPorSituacao,
  hasExactPermission,
  rotuloMemoria,
  type Balance,
  type CalculationMemory,
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
  /** Nome do Devedor, resolvido no servidor. Ausente sem permissao de leitura. */
  devedor?: string | undefined;
  /** Data de hoje, resolvida no servidor. */
  hoje: string;
  initialState: MotorActionState;
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
      <p className="font-semibold text-foreground">Sem permissao</p>
      <p>Seu acesso atual nao permite ver os emprestimos.</p>
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
            {moeda(loan.principal_original)} · desde {formatarData(loan.criado_em)}
          </p>
        </div>
        <Link
          className="shrink-0 rounded-xl border border-border px-3 py-2 text-sm font-semibold text-primary underline-offset-4 hover:underline"
          href={`/app/motor/${loan.id}`}
        >
          Mais informacoes
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
          Separados pela situacao registrada em cada operacao. Abra um emprestimo para ver o extrato e registrar pagamento.
        </p>
      </header>
      {hasExactPermission(permissions, MOTOR_LOAN_CREATE_PERMISSION) ? (
        // O caminho de lancar emprestimo e o wizard em /app/lancamentos. Pedir
        // UUID de Contrato ao Credor e o oposto do que o PLAN-027 decidiu; a
        // criacao por Contrato existente segue possivel, mas recolhida.
        <details className="rounded-2xl border border-border bg-muted/30 p-4">
          <summary className="cursor-pointer text-sm font-semibold">Criar a partir de um contrato ja existente</summary>
          <div className="mt-4">
            <CreateLoanForm action={createAction} initialContractId={initialContractId} initialState={initialState} />
          </div>
        </details>
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
                          <span className="text-lg font-semibold">{moeda(loan.principal_original)}</span>
                          <span className="text-muted-foreground"> · desde {formatarData(loan.criado_em)}</span>
                        </p>
                        <Link
                          className="shrink-0 rounded-xl border border-border px-3 py-2 text-sm font-semibold text-primary underline-offset-4 hover:underline"
                          href={`/app/motor/${loan.id}`}
                        >
                          Mais informacoes
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
  hoje,
  initialState,
  loanId,
  paymentAction,
  permissions,
  renegotiationAction,
  settlementAction,
}: Readonly<{
  hoje: string;
  initialState: MotorActionState;
  loanId: string;
  paymentAction: MotorAction;
  permissions: readonly string[];
  renegotiationAction: MotorAction;
  settlementAction: MotorAction;
}>) {
  return (
    <section className="grid gap-4">
      {hasExactPermission(permissions, MOTOR_PAYMENT_CREATE_PERMISSION) ? (
        <MotorCommandForm action={paymentAction} command="registrar-pagamento" emprestimoId={loanId} hoje={hoje} initialState={initialState} />
      ) : null}
      {hasExactPermission(permissions, MOTOR_SETTLEMENT_EXECUTE_PERMISSION) ? (
        <MotorCommandForm action={settlementAction} command="executar-quitacao" emprestimoId={loanId} hoje={hoje} initialState={initialState} />
      ) : null}
      {hasExactPermission(permissions, MOTOR_RENEGOTIATION_CREATE_PERMISSION) ? (
        <MotorCommandForm action={renegotiationAction} command="registrar-renegociacao" emprestimoId={loanId} hoje={hoje} initialState={initialState} />
      ) : null}
    </section>
  );
}

function LoanOperationsDrawer({
  hoje,
  initialState,
  loanId,
  paymentAction,
  permissions,
  renegotiationAction,
  settlementAction,
}: Readonly<{
  hoje: string;
  initialState: MotorActionState;
  loanId: string;
  paymentAction: MotorAction;
  permissions: readonly string[];
  renegotiationAction: MotorAction;
  settlementAction: MotorAction;
}>) {
  return (
    <Sheet>
      <section className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold">Operacoes do emprestimo</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Registre pagamentos, quite ou renegocie sem sair do contexto desta operacao.
          </p>
        </div>
        <SheetTrigger asChild>
          <Button className="shrink-0" type="button">Operar emprestimo</Button>
        </SheetTrigger>
      </section>
      <SheetContent aria-label="Operacoes deste emprestimo">
        <SheetHeader>
          <SheetTitle>Operacoes deste emprestimo</SheetTitle>
          <SheetDescription>
            Escolha a acao feita no atendimento. Os valores continuam sendo enviados ao Motor; a tela apenas coleta a intencao.
          </SheetDescription>
        </SheetHeader>
        <SheetBody>
          <DetailCommands
            hoje={hoje}
            initialState={initialState}
            loanId={loanId}
            paymentAction={paymentAction}
            permissions={permissions}
            renegotiationAction={renegotiationAction}
            settlementAction={settlementAction}
          />
        </SheetBody>
      </SheetContent>
    </Sheet>
  );
}

/** Numero grande com rotulo curto: a unidade de leitura do painel. */
function Indicador({ destaque, detalhe, rotulo, valor }: Readonly<{ destaque?: boolean; detalhe?: string; rotulo: string; valor: string }>) {
  return (
    <div className={`rounded-2xl border p-4 ${destaque ? "border-primary/40 bg-primary/5" : "border-border bg-card"}`}>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{rotulo}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{valor}</p>
      {detalhe ? <p className="text-sm text-muted-foreground">{detalhe}</p> : null}
    </div>
  );
}

/**
 * Painel do emprestimo: o que o Credor precisa saber sem rolar nem clicar.
 *
 * Quanto emprestou, quanto ainda falta, qual e a proxima parcela e quantas ja
 * foram pagas. Nada aqui e calculado: os valores vem do saldo que o backend
 * devolveu, a proxima parcela e a primeira ainda em aberto na ordem recebida, e
 * a contagem e o tamanho da lista.
 */
/**
 * Painel do emprestimo livre: o que o Credor precisa saber sem rolar nem clicar.
 *
 * Quanto emprestou, quanto ainda deve, quanto de juros correu e quando e o
 * proximo acerto. Nada e calculado aqui: os valores vem do saldo que o backend
 * devolveu, e a data do acerto vem do proprio emprestimo — calcular calendario
 * no navegador duplicaria uma regra de dominio.
 */
function PainelDoEmprestimo({
  balance,
  devedor,
  loan,
}: Readonly<{ balance: MotorReadResult<Balance>; devedor: string | undefined; loan: Loan }>) {
  const situacao = SITUACOES.find((item) => item.estado === loan.estado);
  const pendente = loan.acerto_pendente_desde ?? undefined;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">{devedor ?? "Emprestimo"}</h1>
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ${
            pendente ? "bg-destructive/15 text-destructive" : "bg-secondary text-secondary-foreground"
          }`}
        >
          {pendente ? `Acerto em atraso desde ${formatarData(pendente)}` : (situacao?.titulo ?? loan.estado)}
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Indicador detalhe={`em ${formatarData(loan.criado_em)}`} rotulo="Emprestado" valor={moeda(loan.principal_original)} />
        <Indicador
          destaque
          detalhe={balance.kind === "ready" ? `em ${formatarData(balance.data.data_referencia)}` : "indisponivel agora"}
          rotulo="Deve hoje"
          valor={balance.kind === "ready" ? moeda(balance.data.total) : "--"}
        />
        <Indicador
          detalhe="minimo a receber no acerto"
          rotulo="Juros do periodo"
          valor={balance.kind === "ready" ? moeda(balance.data.juros) : "--"}
        />
        <Indicador
          detalhe={loan.dia_de_acerto ? `todo dia ${loan.dia_de_acerto}` : "sem dia combinado"}
          rotulo="Proximo acerto"
          valor={loan.proximo_acerto_em ? formatarData(loan.proximo_acerto_em) : "--"}
        />
      </div>
    </section>
  );
}

/**
 * Extrato: como o total devido hoje se reparte.
 *
 * Substitui a tabela de parcelas, que deixou de existir com o emprestimo livre
 * (DR-004). O que o devedor deve nao esta congelado num plano — muda a cada dia
 * que passa e a cada amortizacao.
 */
function ExtratoDoSaldo({ balance }: Readonly<{ balance: MotorReadResult<Balance> }>) {
  if (balance.kind !== "ready") return null;
  return (
    <article className="rounded-2xl border border-border bg-card p-4">
      <h2 className="font-semibold">Como esta a divida hoje</h2>
      <dl className="mt-3 grid gap-3 sm:grid-cols-3">
        <RawValue label="Ainda emprestado" value={moeda(balance.data.principal)} />
        <RawValue label="Juros corridos" value={moeda(balance.data.juros)} />
        <RawValue label="Total" value={moeda(balance.data.total)} />
      </dl>
      <p className="mt-3 text-sm text-muted-foreground">
        No acerto o devedor deve, no minimo, os juros. O que pagar alem disso abate o valor emprestado.
      </p>
    </article>
  );
}

function ReadyAuxiliary({ memories, settlementPreview }: Pick<MotorDetailProps, "memories" | "settlementPreview">) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      {settlementPreview.kind === "ready" ? (
        <article className="rounded-2xl border border-border bg-card p-4">
          <h2 className="font-semibold">Valor para quitar hoje</h2>
          <p className="mt-2 text-2xl font-semibold tabular-nums">{moeda(settlementPreview.data.valor_quitacao.valor_total)}</p>
          <dl className="mt-3 grid gap-3 sm:grid-cols-3">
            <RawValue label="Principal" value={moeda(settlementPreview.data.valor_quitacao.componentes.principal)} />
            <RawValue label="Juros" value={moeda(settlementPreview.data.valor_quitacao.componentes.juros)} />
            <RawValue label="Encargos" value={moeda(settlementPreview.data.valor_quitacao.componentes.encargos)} />
          </dl>
        </article>
      ) : null}
      {memories.kind === "ready" && memories.data.length > 0 ? (
        <article className="rounded-2xl border border-border bg-card p-4">
          <h2 className="font-semibold">Como a conta foi feita</h2>
          <div className="mt-3 space-y-3">
            {memories.data.map((memory) => (
              <details className="rounded-xl border border-border bg-muted/30 p-3" key={memory.id}>
                <summary className="cursor-pointer text-sm font-semibold">{rotuloMemoria(memory.tipo)}</summary>
                <ol className="mt-3 space-y-2 pl-5 text-sm">
                  {memory.passos.map((passo, indice) => (
                    <li key={`${memory.id}-${indice}`}>{passo.nome}</li>
                  ))}
                </ol>
                {/* O detalhe tecnico continua acessivel para suporte e auditoria,
                    porem fechado: quem opera nao precisa dele para decidir. */}
                <JsonBlock label="Detalhe tecnico" value={memory} />
              </details>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}

export function MotorDetailPage({
  balance,
  devedor,
  hoje,
  initialState = INITIAL_MOTOR_ACTION_STATE,
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
      {loan.kind === "denied" ? <DeniedPanel /> : null}
      {loan.kind === "problem" ? <ProblemPanel problem={loan.problem} recoveryHref={recoveryHref} /> : null}
      {loan.kind === "ready" ? (
        <>
          <PainelDoEmprestimo balance={balance} devedor={devedor} loan={loan.data} />
          <ExtratoDoSaldo balance={balance} />
          {/* Sem nenhuma permissao de comando o bloco nao existe, em vez de
              abrir vazio e sugerir uma acao indisponivel. */}
          {hasExactPermission(permissions, MOTOR_PAYMENT_CREATE_PERMISSION)
          || hasExactPermission(permissions, MOTOR_SETTLEMENT_EXECUTE_PERMISSION)
          || hasExactPermission(permissions, MOTOR_RENEGOTIATION_CREATE_PERMISSION) ? (
          <LoanOperationsDrawer
            hoje={hoje}
            initialState={initialState}
            loanId={loan.data.id}
            paymentAction={paymentAction}
            permissions={permissions}
            renegotiationAction={renegotiationAction}
            settlementAction={settlementAction}
          />
          ) : null}
          <ReadyAuxiliary memories={memories} settlementPreview={settlementPreview} />
        </>
      ) : null}
    </main>
  );
}
