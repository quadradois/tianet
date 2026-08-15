import { ReportsLoadingState } from "@/components/relatorios/relatorios";

export default function RelatoriosLoading() {
  return (
    <div className="grid gap-5">
      <h1 className="text-3xl font-bold tracking-tight">Relatorios</h1>
      <ReportsLoadingState title="Relatorios operacionais" />
    </div>
  );
}
