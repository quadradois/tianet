import { DestructiveDialogDemo } from "./destructive-dialog-demo";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  NotFoundState,
  PermissionDeniedState,
  SuccessState,
} from "./feedback-state";
import { OverflowRegion } from "./overflow-region";
import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

function PendingButton() {
  return (
    <Button aria-busy="true" disabled type="button" variant="outline">
      Processando exemplo…
    </Button>
  );
}

const tokenRows = [
  ["Superfície", "background / card / muted", "Conteúdo e hierarquia"],
  ["Interação", "primary / border / ring", "Ação, limite e foco"],
  ["Feedback", "success / warning / danger / information", "Estados funcionais"],
  ["Estrutura", "space / size / radius / shadow", "Ritmo e densidade"],
] as const;

function FoundationShowcase() {
  return (
    <div className="grid gap-(--space-section)">
      <header className="grid max-w-3xl gap-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold tracking-[0.12em] text-muted-foreground uppercase">Foundation 1.0</span>
          <span className="rounded-full bg-success-subtle px-3 py-1 text-xs font-semibold text-success-foreground-strong">Base funcional</span>
        </div>
        <div className="grid gap-3">
          <h1 className="text-4xl font-bold tracking-[-0.035em] text-balance sm:text-6xl">Frontend MVP</h1>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            Showcase técnico da fundação visual: tokens neutros, primitives pertencentes ao repositório e estados acessíveis antes das jornadas.
          </p>
        </div>
        <Alert variant="information">
          <AlertTitle>Identidade deliberadamente neutra</AlertTitle>
          <AlertDescription>Marca, paleta final e decisões de produto continuam pendentes. Esta superfície valida função, contraste e composição.</AlertDescription>
        </Alert>
      </header>

      <section aria-labelledby="acoes-title" className="grid gap-5">
        <div className="grid gap-1">
          <h2 className="text-2xl font-semibold tracking-tight" id="acoes-title">Ações e formulário</h2>
          <p className="text-sm leading-6 text-muted-foreground">Estados distintos, alvos confortáveis e labels explícitos.</p>
        </div>
        <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
          <Card data-motion-sample>
            <CardHeader>
              <CardTitle>Variantes explícitas</CardTitle>
              <CardDescription>As variantes expressam intenção sem combinar props booleanas conflitantes.</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-3">
              <Button type="button">Ação principal</Button>
              <Button type="button" variant="outline">Ação secundária</Button>
              <Button type="button" variant="success">Confirmar exemplo</Button>
              <Button disabled type="button">Indisponível</Button>
              <PendingButton />
              <DestructiveDialogDemo />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Entrada rotulada</CardTitle>
              <CardDescription>Validação de experiência não substitui a fonte responsável.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-3">
                <Label htmlFor="foundation-reference">Referência técnica</Label>
                <Input
                  autoComplete="off"
                  id="foundation-reference"
                  name="foundation-reference"
                  placeholder="Ex.: amostra acessível…"
                />
                <p className="text-xs leading-5 text-muted-foreground">Dado sensível demonstrativo: •••• A7X9</p>
                <Button type="button" variant="outline">Validar interação</Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </section>

      <section aria-labelledby="estados-title" className="grid gap-5">
        <div className="grid gap-1">
          <h2 className="text-2xl font-semibold tracking-tight" id="estados-title">Estados estruturais</h2>
          <p className="text-sm leading-6 text-muted-foreground">Loading, vazio, erro, sucesso, permissão e 404 neutro são componentes explícitos.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <LoadingState />
          <EmptyState />
          <ErrorState />
          <SuccessState />
          <PermissionDeniedState />
          <NotFoundState />
        </div>
      </section>

      <section aria-labelledby="overflow-title" className="grid gap-5">
        <div className="grid gap-1">
          <h2 className="text-2xl font-semibold tracking-tight" id="overflow-title">Overflow governado</h2>
          <p className="text-sm leading-6 text-muted-foreground">A região larga recebe nome, foco e rolagem própria sem expandir o documento.</p>
        </div>
        <OverflowRegion label="Mapa de tokens da foundation">
          <table className="w-full min-w-3xl border-collapse text-left text-sm">
            <caption className="sr-only">Categorias de tokens semânticos da foundation</caption>
            <thead className="bg-muted text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-semibold" scope="col">Categoria</th>
                <th className="px-4 py-3 font-semibold" scope="col">Tokens</th>
                <th className="px-4 py-3 font-semibold" scope="col">Responsabilidade</th>
              </tr>
            </thead>
            <tbody>
              {tokenRows.map(([category, tokens, responsibility]) => (
                <tr className="border-t border-border" key={category}>
                  <th className="px-4 py-3 font-semibold" scope="row">{category}</th>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{tokens}</td>
                  <td className="px-4 py-3">{responsibility}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </OverflowRegion>
      </section>
    </div>
  );
}

export { FoundationShowcase, PendingButton };
