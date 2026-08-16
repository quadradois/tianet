"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AppError({ error, reset }: Readonly<{ error: Error & { digest?: string }; reset(): void }>) {
  useEffect(() => { void error; }, [error]);
  return (
    <Card role="alert">
      <CardHeader>
        <CardTitle>Nao foi possivel apresentar o conteudo</CardTitle>
        <CardDescription>A falha foi contida nesta area. Tente novamente.</CardDescription>
      </CardHeader>
      <CardContent><Button onClick={reset} type="button">Tentar novamente</Button></CardContent>
    </Card>
  );
}
