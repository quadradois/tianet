import { ConfiguracoesLoadingState } from "@/components/configuracoes-financeiras/configuracoes-financeiras";

export default function Loading() {
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <ConfiguracoesLoadingState title="Configuracoes cadastradas" />
      <ConfiguracoesLoadingState title="Configuracao vigente" />
      <ConfiguracoesLoadingState title="Modalidades" />
      <ConfiguracoesLoadingState title="Calendarios" />
    </div>
  );
}
