import { SessionRecovery } from "@/components/auth/session-recovery.client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SessionRecoveryPage() {
  return (
    <main className="grid min-h-screen place-items-center px-5 py-10" id="conteudo-principal" tabIndex={-1}>
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Validando sua sessao</CardTitle>
          <CardDescription>O contexto continua sendo resolvido exclusivamente pelo backend.</CardDescription>
        </CardHeader>
        <CardContent><SessionRecovery /></CardContent>
      </Card>
    </main>
  );
}
