# Wizard de Lancamento - Discovery/SDD

**Tipo:** Artefato de Discovery/SDD

**Versao:** 1.0.0

**Status:** Em revisao — nao autoriza implementacao

---

# 1. Objetivo

Permitir que o Credor lance um emprestimo em um fluxo unico, informando o
devedor e as condicoes, sem percorrer as seis transicoes de estado que a
interface exige hoje.

Este discovery nao propoe capacidade de negocio nova. Propoe um **caminho novo
para capacidades que ja existem**, e a operacao de backend que o torna atomico.

---

# 2. Autoridades consultadas

- `docs/foundation/FOUNDATION-001-product-vision.md` v2.0.0 — publico corrigido;
- `docs/governance/decision-requests/DR-002-...` — opacidade dos parametros;
- `docs/operations/contexto-externo.md` — integracao Evolution Go;
- `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md` — contrato do canal;
- `docs/governance/frontend-mvp-traceability-matrix.md` v3.3.0;
- codigo: `infrastructure/unit_of_work.py`, `domain/credit/proposta_comercial.py`,
  `domain/credit/contrato_credito.py`, `domain/credit/motor_financeiro.py`.

---

# 3. Contexto — por que existe cerimonia para remover

`FOUNDATION-001 §3` descrevia o publico como financeiras e correspondentes. Dessa
premissa derivou corretamente a separacao entre quem propoe e quem aprova, e dela
a maquina de estados de Proposta e Contrato.

A premissa estava errada: o produto e para quem empresta o proprio dinheiro e
opera sozinho. Para essa pessoa, as seis etapas sao a mesma pessoa clicando seis
vezes em si mesma.

**Mas a separacao de funcoes nao desaparece** — ela muda de par. O segundo
operador e o agente de IA que atende o WhatsApp (`FOUNDATION-001 §3.1`). Por isso
Proposta com aprovacao **permanece**: e a caixa de entrada do agente, nao
burocracia herdada.

Consequencia de desenho: existe **uma operacao** com **duas origens**.

```
Credor digita (wizard) ─────┐
                            ├──▶ LANCAR EMPRESTIMO ──▶ comprovante
Agente pre-cadastra ────────┘        (uma transacao)
(Credor aprova)
```

Este discovery cobre a primeira origem e a operacao. A segunda depende de
decisao pendente (secao 11).

---

# 4. Escopo

1. **Operacao composta de lancamento** — servico de aplicacao que resolve ou cria
   o Devedor, percorre Proposta e Contrato, cria o Emprestimo e gera o plano de
   parcelas, tudo sob um unico `UnitOfWork`.
2. **Endpoint** que expoe a operacao, com `Idempotency-Key` obrigatoria.
3. **Wizard** de tres passos na interface.
4. **Tela de emprestimos** com em andamento, quitados e encerrados.
5. **Detalhe do Devedor** exibindo a situacao dos emprestimos dele.
6. **Comprovante** gerado no backend e enfileirado para envio.

---

# 5. Fora do escopo

- Recebimento de mensagens e pre-cadastro pelo agente (Fase 3);
- provisionamento de tenant/instancia Evolution e fluxo de QR (Fase 1 da
  integracao WhatsApp — pre-requisito do envio, nao do wizard);
- remocao das telas passo a passo existentes: elas continuam alcancaveis;
- alteracao de qualquer regra do Motor Financeiro;
- administracao integral de Usuarios (Lacuna 7 do PLAN-025, segue aberta).

---

# 6. A operacao composta

## 6.1 Por que cabe em uma transacao

`SqlAlchemyUnitOfWork` ja instancia **todos** os repositorios sobre a mesma
sessao — `devedor`, `proposta_comercial`, `contrato_credito`, `emprestimo`,
`parcela`. A infraestrutura para compor a cadeia atomicamente ja existe e nunca
foi usada assim. O grafo confirma a centralidade: `UnitOfWork` e o no mais
conectado do sistema, com 340 arestas.

`AD-001` (uma transacao por caso de uso) e satisfeito por construcao.

## 6.2 O que a operacao faz

Em sequencia, sob um unico commit:

| Passo | Efeito |
|---|---|
| 1 | resolve o Devedor por id, ou cria um novo com documento, nome e contato |
| 2 | cria a Proposta e a leva a `aprovada` |
| 3 | formaliza o Contrato, assina e libera para o Motor |
| 4 | cria o Emprestimo |
| 5 | gera o plano de parcelas |

**As invariantes nao sao contornadas, sao executadas.** Cada transicao passa pelo
metodo do agregado, com `usuario_id` e registro de decisao. A trilha de auditoria
fica completa: quem olhar o historico ve as seis transicoes, com o mesmo ator e o
mesmo instante.

Falha em qualquer passo desfaz tudo. Nao existe estado orfao — hoje, com oito
chamadas HTTP separadas, existe.

## 6.3 Fronteira do envio

O comprovante **nao** e enviado dentro da transacao. Commit primeiro, depois
enfileira a notificacao; o worker do Scheduler envia e registra em
`RegistroComunicacao`. Se o WhatsApp estiver fora do ar, o emprestimo existe
mesmo assim, e o worker reprocessa.

## 6.4 Contrato HTTP proposto

```
POST /credit/carteiras/{carteira_id}/lancamentos
Idempotency-Key: obrigatoria
```

O nome evita colisao: `POST /credit/contratos/{contrato_id}/emprestimos` ja existe
e significa outra coisa. `lancamento` e a palavra que o Credor usa.

---

# 7. O wizard

Tres passos. O terceiro e confirmacao, nao formulario.

## 7.1 Passo 1 — Devedor

Busca por nome ou documento entre os devedores da Carteira. Se nao existir,
cadastra ali mesmo: documento, nome e um contato de WhatsApp.

O contato de WhatsApp deixa de ser opcional quando o comprovante existir — sem
numero nao ha para onde enviar.

## 7.2 Passo 2 — Condicoes

Quatro campos, todos digitados pelo Credor no ato:

| Campo | Observacao |
|---|---|
| valor | sem valor padrao |
| taxa de juros mensal | sem valor padrao |
| quantidade de parcelas | exigida pelo Motor |
| data do primeiro vencimento | exigida pelo Motor |

**Sao campos tipados, nao JSON.** A textarea de JSON cru existente permanece nas
telas antigas; o wizard nao a reproduz.

## 7.3 Passo 3 — Confirmacao

Mostra o que sera criado e um unico botao. Depois da confirmacao, a tela do
emprestimo abre com o plano de parcelas que o Motor gerou.

---

# 8. Tela de emprestimos

Tres grupos, derivados do estado que o backend retorna:

| Grupo | Significado |
|---|---|
| Em andamento | ha saldo em aberto |
| Quitados | 100% pago — a definicao de "finalizado" |
| Encerrados | cancelados ou encerrados sem quitacao |

O terceiro grupo existe porque cancelado e encerrado nao sao quitados nem estao
em andamento; sem ele, sumiriam da interface.

---

# 9. Devedor com o emprestimo junto

O detalhe do Devedor passa a exibir a situacao dos emprestimos dele, sem exigir
navegacao para o Motor. Somente leitura, e somente valores retornados pelo
backend.

---

# 10. Comprovante

Texto gerado **no backend**, por tres motivos: os valores sao financeiros e o
backend e a autoridade; o scanner anti-calculo proibe aritmetica no frontend; e o
agente de WhatsApp vai precisar do mesmo comprovante — um template serve os dois.

Conteudo: partes, valor, taxa, quantidade de parcelas, datas e valores de cada
parcela conforme o Motor gerou. Sem valor juridico; resolve "o que a gente
combinou mesmo?".

Entrega pelo canal Evolution Go, como implementacao de `NotificationChannel` ao
lado do Resend. **Depende da Fase 1 da integracao** (instancia conectada); ate la
o texto pode ser gerado e exibido para copia manual.

---

# 11. Decisoes pendentes

1. **Previa do plano antes de confirmar.** Mostrar "6 parcelas de aproximadamente
   2.070" antes do Credor confirmar tem valor obvio para quem decide emprestar.
   Mas o frontend nao pode calcular, e **nao existe endpoint de simulacao que
   compute sem persistir** — as 107 operacoes nao incluem dry-run do Motor.
   Ou se cria um, ou o MVP confirma primeiro e mostra o plano depois.
2. **Topologia do agente** — webhook na TiaNet ou o agente chamando a API. Nao
   bloqueia o wizard; bloqueia a Fase 3.
3. **Nome do endpoint** — `lancamentos` e proposta, nao decisao.

---

# 12. Riscos

| Risco | Tratamento |
|---|---|
| Dupla submissao criando dois emprestimos | `Idempotency-Key` obrigatoria |
| Operacao longa em uma transacao | medir; o plano de parcelas e o passo mais pesado |
| Comprovante travar o lancamento | envio fora da transacao, via worker |
| Wizard divergir do que o Motor aceita | cenario de jornada real contra backend real, como o IMP-304 |
| Telas antigas e wizard divergirem | ambos chamam a mesma operacao composta |

---

# 13. Plano de testes

- **Unidade:** montagem do comprovante; validacao dos quatro campos.
- **Integracao:** a operacao composta em uma transacao; rollback em falha de cada
  passo; replay com a mesma `Idempotency-Key`.
- **Contrato:** o endpoint novo no OpenAPI; cliente tipado regenerado.
- **Jornada real:** wizard preenchido na interface contra FastAPI e PostgreSQL
  reais, ate o plano de parcelas — o cenario que faltava e deixou o defeito da
  DR-002 passar.

---

# 14. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-16 | Discovery do wizard de lancamento, da operacao composta e das telas de emprestimo. |
