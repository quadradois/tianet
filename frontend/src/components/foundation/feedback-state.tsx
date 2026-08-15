import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "../ui/alert";
import { Skeleton } from "../ui/skeleton";

type StateFrameProps = Readonly<{
  action?: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
}>;

function StateFrame({ action, description, eyebrow, title }: StateFrameProps) {
  return (
    <div className="grid min-h-44 content-start gap-4 rounded-lg border border-border bg-background p-5">
      <div className="grid gap-1">
        <span className="text-xs font-semibold tracking-[0.12em] text-muted-foreground uppercase">{eyebrow}</span>
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {action ? <div className="mt-auto">{action}</div> : null}
    </div>
  );
}

function LoadingState() {
  return (
    <div aria-label="Carregando conteúdo" aria-live="polite" aria-busy="true" className="grid min-h-44 content-start gap-4 rounded-lg border border-border bg-background p-5" role="status">
      <span className="sr-only">Carregando conteúdo</span>
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-5 w-3/5" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
    </div>
  );
}

function EmptyState() {
  return (
    <StateFrame
      description="Ainda não há conteúdo para apresentar neste recorte."
      eyebrow="Estado vazio"
      title="Nenhum item disponível"
    />
  );
}

function ErrorState() {
  return (
    <Alert className="min-h-44 content-start" role="alert" variant="danger">
      <AlertTitle>Não foi possível concluir</AlertTitle>
      <AlertDescription>A tentativa foi preservada. Tente novamente quando estiver pronto.</AlertDescription>
    </Alert>
  );
}

function SuccessState() {
  return (
    <Alert aria-live="polite" className="min-h-44 content-start" role="status" variant="success">
      <AlertTitle>Operação concluída</AlertTitle>
      <AlertDescription>A confirmação veio da fonte responsável e pode ser apresentada com segurança.</AlertDescription>
    </Alert>
  );
}

function PermissionDeniedState() {
  return (
    <StateFrame
      description="Este conteúdo não está disponível para o contexto atual."
      eyebrow="Acesso"
      title="Permissão necessária"
    />
  );
}

function NotFoundState() {
  return (
    <StateFrame
      description="O recurso solicitado não foi encontrado ou não está disponível."
      eyebrow="404 neutro"
      title="Conteúdo indisponível"
    />
  );
}

export {
  EmptyState,
  ErrorState,
  LoadingState,
  NotFoundState,
  PermissionDeniedState,
  SuccessState,
};
