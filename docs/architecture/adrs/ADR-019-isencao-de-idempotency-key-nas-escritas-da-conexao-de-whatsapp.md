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

### A premissa foi medida em 2026-09-04, e é FALSA

> **Esta seção mudou de sentido.** Ela registrava uma premissa não certificada.
> O time que mantém o Evolution Go respondeu com leitura do código-fonte
> (`docs/whatsapp/2026-09-04-resposta-esclarecimento-evolution.md` §3.1), e a
> premissa **não se sustenta**.

Para `DELETE /platform/whatsapp/conexao`, o lado da TiaNet converge:
`desparear()` sobre conexão já despareada é no-op, coberto por teste. **Isso
continua verdadeiro.**

**O lado do provedor NÃO converge.** `POST /instance/logout` numa instância já
desconectada **nunca retorna 2xx — sempre `400`**. O fluxo passa por
`ensureClientConnected`, que devolve `"no active session found"` ou
`"client disconnected"`, e o handler responde `400`. Não é comportamento que eles
pretendam mudar.

O adapter recusava qualquer resposta não-2xx, então **a segunda chamada falhava**.
Não era risco teórico: era defeito em produção esperando a primeira desconexão
repetida.

**Consertado em 2026-09-04 (IMP-371):** `EvolutionInstanciaClient.desconectar`
trata **qualquer `400` de `/instance/logout`** como sucesso equivalente a "já
desconectado" — do mesmo jeito que já tratava `record not found` na exclusão. O
`400` não é filtrado por texto, e essa recusa é recomendação deles: a mensagem
exata depende do timing da autocura interna, então discriminar por texto seria
frágil. Aqui casar pelo status é seguro porque a rota não recebe payload — não há
outro motivo para ela responder `400`.

**A decisão da ADR não muda.** A isenção de `Idempotency-Key` continua válida, e
por um motivo que ficou mais forte, não mais fraco: a chave replayaria o
resultado do nosso lado sem dizer nada sobre o estado no provedor — e agora
sabemos que o estado no provedor responde `400`. O que muda é o **adapter**, não
o contrato.

**Com o conserto, a convergência do `DELETE` volta a valer de ponta a ponta**: o
lado da TiaNet já era no-op, e agora o lado do provedor também não reclama de uma
desconexão repetida.

## Consequências

**Positivas**

- A exceção deixa de contradizer a regra: passa a ser parte dela, por referência.
- Quem revisar encontra a resposta no lugar onde decisões arquiteturais moram,
  em vez de dentro de um backlog de execução.
- A premissa não certificada ficou visível para quem foi validar — e foi
  justamente por estar escrita que ela pôde ser refutada.

**Negativas, e assumidas**

- Não há detecção de reenvio acidental nessas três rotas. O custo é baixo porque
  nenhuma delas produz resultado de negócio novo em repetição — mas é custo.
- A isenção é **fechada**: vale para estas três operações e nada mais. Qualquer
  escrita nova da conexão de WhatsApp nasce sob a regra 3, e sair dela exige
  emendar esta ADR.

**Quando esta decisão deve ser reaberta**

1. ~~Quando o comportamento do Evolution para `logout` repetido for observado.~~
   **Observado em 2026-09-04: ele recusa, com `400`.** A justificativa do `DELETE`
   sobrevive — o que falta é o tratamento explícito de "já desconectado" no
   adapter, registrado acima e ainda não implementado.
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
| 1.2.0 | 04/09/2026 | O conserto saiu (IMP-371): `desconectar` trata qualquer `400` de `/instance/logout` como "ja desconectado", com dois testes que fixam o status como criterio e a frase como irrelevante. A secao da premissa deixa de descrever um defeito ativo e passa a descrever um defeito fechado. |
| 1.1.0 | 04/09/2026 | A premissa da convergência do `logout` foi medida — e e falsa. O time do Evolution Go respondeu por leitura de codigo: `POST /instance/logout` numa instancia ja desconectada **sempre** retorna `400`, e nosso adapter recusa nao-2xx, entao a segunda chamada falha hoje em producao. A decisao da ADR nao muda e ate se fortalece; o que muda e o adapter, que deve tratar qualquer `400` dessa rota como "ja desconectado" — sem filtrar por texto, porque a mensagem depende de timing interno deles. |
| 1.0.0 | 03/09/2026 | Decisão registrada. A isenção existia desde o IMP-367 e foi cobrada por quatro rodadas de review porque morava num plano de execução, não numa ADR — a §3.1 do PLAN-034 chegou a prever a terceira cobrança e ainda assim não impediu a quarta. Promove o raciocínio existente sem alterá-lo, separa os três motivos (que não são o mesmo) e declara como premissa, não como fato, a convergência do `logout` no provedor — que segue sem ambiente onde ser medida. |
