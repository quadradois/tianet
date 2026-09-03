# ADR-019: Isenção de Idempotency-Key nas escritas da conexão de WhatsApp

> **Status:** Aceito
> **Data:** 2026-09-03
> **Autor(es):** Engenharia
> **Revisor(es):** Codex (quatro rodadas adversariais)
> **Aprovação:** Fundador / 2026-09-03
> **Substitui:** —
> **Substituído por:** —

---

## Contexto

A regra 3 do `CLAUDE.md` estabelece `Idempotency-Key` **obrigatória em todo
POST/PATCH de escrita**. As três escritas da conexão de WhatsApp (IMP-368) não a
exigem, e a justificativa vive no PLAN-034 §3.1 — um plano de execução.

**O problema não é o raciocínio; é onde ele mora.** A §3.1 termina com a frase:

> *"Três rodadas de review adversarial cobraram a chave; a decisão está aqui
> para que a quarta encontre a resposta em vez da pergunta."*

Em 2026-09-03 a **quarta rodada cobrou a chave de novo**, classificando a
omissão como **bloqueante** por contrariar o `CLAUDE.md`. O revisor estava certo
sobre a regra: exceção justificada dentro de um plano de execução não é exceção
à regra arquitetural — é uma contradição entre dois documentos, e quem chega
sem contexto lê a regra.

Agrava o quadro que **`/CLAUDE.md` está no `.gitignore`** (linha 43). A regra que
o revisor citou vive em arquivo não versionado: um clone limpo não a possui, e
emenda feita nela não viaja para máquina nenhuma. Registrar a exceção lá seria
registrá-la em lugar que o repositório não conhece.

## Decisão

**A isenção é mantida, e passa a ser decisão arquitetural registrada aqui.**

Ficam isentas de `Idempotency-Key` exatamente estas três operações:

| Operação | Por que a chave não se aplica |
|---|---|
| `POST /platform/whatsapp/conexao` | O resultado é um **QR que expira em ~20s** e que o provedor rotaciona sozinho. O contrato da idempotência é "a mesma chave devolve o mesmo resultado" — e devolver o QR da primeira chamada seria devolver algo que já não pareia nada. O efeito externo a proteger é o **nascimento da instância**, e ele já está serializado por advisory lock no Tenant mais `UNIQUE (tenant_id)`. Não há payload divergente a detectar porque **não há payload**: o nome da instância é derivado do Tenant desde o IMP-368. |
| `DELETE /platform/whatsapp/conexao` | Não há resultado de negócio a replayar: o desfecho é a **ausência** de pareamento, e repetir pede o mesmo estado final. Ver a premissa declarada abaixo. |
| `DELETE /platform/whatsapp/conexao/instancia` | Apagar é convergente por definição, e o adapter trata `record not found` do provedor **como sucesso** — comportamento observado, não suposto. Uma chave guardaria o resultado de uma exclusão que já aconteceu. |

**Os três motivos não são o mesmo motivo**, e a distinção importa: o do `POST` é
*resultado irreplayável*; o do `DELETE` da instância é *convergência verificada
no provedor*; o do `DELETE` do pareamento é **convergência assumida** — e é o
mais fraco dos três.

### Premissa declarada, e não escondida

Para `DELETE /platform/whatsapp/conexao`, o lado da TiaNet converge:
`desparear()` sobre conexão já despareada é no-op, coberto por teste.

**O lado do provedor não foi certificado.** Não foi observado o que o Evolution
responde a um `logout` repetido, e o adapter recusa qualquer resposta não-2xx —
de modo que, se o provedor tratar o caso como erro, a segunda chamada falha em
vez de convergir. Não existe ambiente de teste do Evolution
(`docs/operations/contexto-externo.md` §2.1), então a verificação só pode
acontecer em produção, com o número do fundador.

Enquanto isso não for medido, **esta é uma premissa, não um fato**, e está
escrita como tal na isenção do guardrail. Adotar `Idempotency-Key` não
resolveria isso: a chave replayaria o resultado do nosso lado sem dizer nada
sobre o estado no provedor.

## Consequências

**Positivas**

- A exceção deixa de contradizer a regra: passa a ser parte dela, por referência.
- Quem revisar encontra a resposta no lugar onde decisões arquiteturais moram,
  em vez de dentro de um backlog de execução.
- A premissa não certificada fica visível para quem for validar em produção.

**Negativas, e assumidas**

- Não há detecção de reenvio acidental nessas três rotas. O custo é baixo porque
  nenhuma delas produz resultado de negócio novo em repetição — mas é custo.
- A isenção é **fechada**: vale para estas três operações e nada mais. Qualquer
  escrita nova da conexão de WhatsApp nasce sob a regra 3, e sair dela exige
  emendar esta ADR.

**Quando esta decisão deve ser reaberta**

1. Quando o comportamento do Evolution para `logout` repetido for observado. Se
   ele recusar, o `DELETE` do pareamento perde sua justificativa e precisa de
   tratamento explícito de "já desconectado" **ou** da chave.
2. Quando alguma dessas rotas passar a produzir resultado de negócio replayável
   — por exemplo, se o `POST` deixar de devolver o QR e passar a devolver um
   identificador estável.
3. Quando houver mais de um operador concorrente. Hoje o sistema é single-tenant
   com um operador (ADR-003), e o reenvio acidental tem uma origem só.

## Alternativas consideradas

**Implementar `Idempotency-Key` nas três.** Exigiria separar o provisionamento
idempotente da obtenção do QR — que não pode ser replayado — e persistir o
resultado dos dois `DELETE`. É trabalho real, de escopo próprio, para proteger
contra um reenvio que não produz efeito novo. Rejeitada por desproporção, não
por dificuldade.

**Deixar como caveat no backlog.** Rejeitada: é o que já existia de fato, e foi
exatamente isso que permitiu a quarta rodada reabrir. Caveat registra dívida;
não resolve contradição entre dois documentos normativos.

## Referências

- `CLAUDE.md` regra 3 — a regra geral. **Não versionado** (`.gitignore` linha 43)
- [PLAN-034 §3.1](../../implementation/plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md) — o raciocínio original, que esta ADR promove
- [ADR-003](ADR-003-escopo-single-tenant-do-v1.md) — single-tenant, um operador
- [ADR-009](ADR-009-notifications-channels.md) — idempotência no canal de notificações
- `docs/operations/contexto-externo.md` §2.1 — ausência de ambiente de teste do Evolution

---

## Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 03/09/2026 | Decisão registrada. A isenção existia desde o IMP-367 e foi cobrada por quatro rodadas de review porque morava num plano de execução, não numa ADR — a §3.1 do PLAN-034 chegou a prever a terceira cobrança e ainda assim não impediu a quarta. Promove o raciocínio existente sem alterá-lo, separa os três motivos (que não são o mesmo) e declara como premissa, não como fato, a convergência do `logout` no provedor — que segue sem ambiente onde ser medida. |
