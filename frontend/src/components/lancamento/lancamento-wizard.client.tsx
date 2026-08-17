"use client";

import Link from "next/link";
import { useActionState, useState } from "react";

import type { LancamentoActionState } from "../../lib/lancamento/lancamento-policy";
import { cpfValido, validarCondicoes, validarDevedor } from "../../lib/lancamento/lancamento-policy";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: LancamentoActionState, formData: FormData) => Promise<LancamentoActionState>;

export type DevedorResumo = Readonly<{ id: string; nome: string; documento: string }>;

type WizardProps = Readonly<{
  action: Action;
  devedores: readonly DevedorResumo[];
  initialState: LancamentoActionState;
}>;

const PASSOS = ["Devedor", "Condicoes", "Confirmacao"] as const;

export function LancamentoWizard({ action, devedores, initialState }: WizardProps) {
  const [state, formAction, pending] = useActionState(action, initialState);
  const [passo, setPasso] = useState(0);
  const [devedorId, setDevedorId] = useState("");
  const [documento, setDocumento] = useState("");
  const [nome, setNome] = useState("");
  const [contatoWhatsapp, setContatoWhatsapp] = useState("");
  const [valor, setValor] = useState("");
  const [taxa, setTaxa] = useState("");
  const [parcelas, setParcelas] = useState("");
  const [primeiroVencimento, setPrimeiroVencimento] = useState("");

  const errosDevedor = validarDevedor(
    devedorId ? { devedorId } : { documento, nome, contatoWhatsapp },
  );
  const errosCondicoes = validarCondicoes({ valor, taxa, parcelas, primeiroVencimento });
  const escolhido = devedores.find((devedor) => devedor.id === devedorId);

  if (state.kind === "success" && state.emprestimoId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Emprestimo lancado</CardTitle>
          <CardDescription>
            O plano de parcelas foi gerado pelo Motor. Correlation ID: {state.correlationId}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link className="underline" href={`/app/motor/${state.emprestimoId}`}>
            Abrir o emprestimo
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Novo emprestimo</CardTitle>
        <CardDescription>
          Passo {passo + 1} de {PASSOS.length}: {PASSOS[passo]}. O Motor calcula os valores; esta
          tela apenas envia o que voce informar.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form action={formAction} className="grid gap-4">
          {/* Todos os campos permanecem montados: trocar de passo nao pode perder
              o que ja foi digitado, e o envio leva o formulario inteiro. */}
          <div className={passo === 0 ? "grid gap-4" : "hidden"}>
            {devedores.length ? (
              <div className="grid gap-2">
                <Label htmlFor="devedor_id">Devedor ja cadastrado</Label>
                <select
                  className="rounded-md border bg-background p-2"
                  id="devedor_id"
                  name="devedor_id"
                  onChange={(event) => setDevedorId(event.target.value)}
                  value={devedorId}
                >
                  <option value="">Cadastrar um novo devedor</option>
                  {devedores.map((devedor) => (
                    <option key={devedor.id} value={devedor.id}>
                      {devedor.nome} — {devedor.documento}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            {devedorId ? null : (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="documento">CPF</Label>
                  <Input
                    aria-describedby="documento-ajuda"
                    id="documento"
                    inputMode="numeric"
                    name="documento"
                    onChange={(event) => setDocumento(event.target.value)}
                    placeholder="000.000.000-00"
                    value={documento}
                  />
                  <p className="text-sm text-muted-foreground" id="documento-ajuda">
                    {documento && !cpfValido(documento)
                      ? "CPF invalido: confira os numeros digitados."
                      : "Com ou sem pontuacao."}
                  </p>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="nome">Nome</Label>
                  <Input
                    id="nome"
                    name="nome"
                    onChange={(event) => setNome(event.target.value)}
                    value={nome}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="contato_whatsapp">WhatsApp</Label>
                  <Input
                    id="contato_whatsapp"
                    name="contato_whatsapp"
                    onChange={(event) => setContatoWhatsapp(event.target.value)}
                    value={contatoWhatsapp}
                  />
                  <p className="text-sm text-muted-foreground">
                    Destino do comprovante do emprestimo.
                  </p>
                </div>
              </>
            )}
          </div>

          <div className={passo === 1 ? "grid gap-4" : "hidden"}>
            <div className="grid gap-2">
              <Label htmlFor="valor">Valor emprestado</Label>
              <Input
                id="valor"
                inputMode="decimal"
                name="valor"
                onChange={(event) => setValor(event.target.value)}
                value={valor}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="taxa">Juros ao mes (%)</Label>
              <Input
                aria-describedby="taxa-ajuda"
                id="taxa"
                inputMode="numeric"
                name="taxa"
                onChange={(event) => setTaxa(event.target.value)}
                placeholder="5"
                value={taxa}
              />
              <p className="text-sm text-muted-foreground" id="taxa-ajuda">
                Numero inteiro. Digite 5 para 5% ao mes.
              </p>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="parcelas">Quantidade de parcelas</Label>
              <Input
                id="parcelas"
                inputMode="numeric"
                name="parcelas"
                onChange={(event) => setParcelas(event.target.value)}
                value={parcelas}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="primeiro_vencimento">Primeiro vencimento</Label>
              <Input
                id="primeiro_vencimento"
                name="primeiro_vencimento"
                onChange={(event) => setPrimeiroVencimento(event.target.value)}
                type="date"
                value={primeiroVencimento}
              />
            </div>
          </div>

          <div className={passo === 2 ? "grid gap-3" : "hidden"}>
            <dl className="grid gap-2 text-sm">
              <div>
                <dt className="text-muted-foreground">Devedor</dt>
                <dd>{escolhido ? `${escolhido.nome} — ${escolhido.documento}` : `${nome} — ${documento}`}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Valor</dt>
                <dd>{valor}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Juros ao mes</dt>
                <dd>{taxa ? `${taxa}%` : ""}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Parcelas</dt>
                <dd>{parcelas}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Primeiro vencimento</dt>
                <dd>{primeiroVencimento}</dd>
              </div>
            </dl>
            <p className="text-sm text-muted-foreground">
              O plano de parcelas aparece depois da confirmacao, calculado pelo Motor.
            </p>
            <Button disabled={pending} type="submit">
              {pending ? "Lancando..." : "Confirmar lancamento"}
            </Button>
          </div>

          <div className="flex gap-2">
            {passo > 0 ? (
              <Button onClick={() => setPasso(passo - 1)} type="button" variant="outline">
                Voltar
              </Button>
            ) : null}
            {passo < 2 ? (
              <Button
                disabled={passo === 0 ? errosDevedor.length > 0 : errosCondicoes.length > 0}
                onClick={() => setPasso(passo + 1)}
                type="button"
              >
                Continuar
              </Button>
            ) : null}
          </div>

          <p aria-live="polite" className="text-sm text-muted-foreground">
            {state.message}
            {state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
