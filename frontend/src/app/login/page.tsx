import { LoginForm } from "@/components/auth/login-form.client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center px-5 py-10" id="conteudo-principal" tabIndex={-1}>
      <Card className="w-full max-w-md">
        <CardHeader>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">TIANET</p>
          <CardTitle className="text-balance">Acesse sua operacao</CardTitle>
          <CardDescription className="text-pretty">Entre com seu e-mail e senha. Sua carteira sera carregada automaticamente.</CardDescription>
        </CardHeader>
        <CardContent><LoginForm /></CardContent>
      </Card>
    </main>
  );
}
