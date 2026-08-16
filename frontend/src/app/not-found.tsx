import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function NotFound() {
  return (
    <main className="grid min-h-screen place-items-center px-5 py-10" id="conteudo-principal" tabIndex={-1}>
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Conteudo indisponivel</CardTitle>
          <CardDescription>O recurso solicitado nao foi encontrado ou nao esta disponivel.</CardDescription>
        </CardHeader>
        <CardContent><Button asChild><Link href="/app">Voltar ao inicio</Link></Button></CardContent>
      </Card>
    </main>
  );
}
