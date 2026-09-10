# PLAN-033 — Copilot TiaNet

**ID:** PLAN-033

**Versao:** 1.2.0

**Status:** Em execucao — GATE-E1a cumprido; GATE-E1b parcial (IMP-352
cumprido em 2026-08-31, resta IMP-359, sequenciado depois do PLAN-034)

**Backlog de execucao:**
`docs/implementation/backlogs/PLAN-033-execution-backlog.md`

> **A fonte de execucao e o backlog.** Este plano existe para o que a governanca
> exige de um documento de plano: objetivo, escopo, contrato de API e gates. O
> detalhe de cada IMP, com criterio de pronto e evidencia, vive no backlog.

---

# 1. Objetivo

Dar forma ao segundo operador previsto no
`docs/foundation/FOUNDATION-001-product-vision.md`: um copilot que deixa a
operadora conversar com o sistema no WhatsApp, onde ela ja trabalha, e que faz o
sistema falar primeiro quando ha algo a dizer.

O plano nasceu de um desenho refutado por revisao adversarial e reescrito. O
veredito e as premissas verificadas estao no backlog, §1 e §2.

---

# 2. Decisoes formais

| Decisao | Onde |
|---|---|
| BYOK: o cliente traz a chave do provedor de IA; API compativel com OpenAI | DR-005 |
| Piloto proposto via OpenRouter, modelo gratuito nominal com tools nativas; NVIDIA direta apenas na comparacao sintetica sob os termos atuais | DR-005, adendo de 2026-09-09 |
| OmniRoute pode ser avaliado como gateway privado opcional, sem `auto`, combo ou fallback e bloqueado enquanto sintetizar tool-calls textuais | Plano agentic v1.4.0 e discovery OmniRoute de 2026-09-09 |
| Preparacao administrativa local testa login ChatGPT pelo Codex App Server oficial; OpenRouter, NVIDIA e OmniRoute ficam em espera durante a prova, sem serem removidos como alternativas | ADR-020 e plano OpenAI/Codex de 2026-09-09 |
| PII liberada no prompt, com ADR-016 intacta para logs | DR-005 §1 |
| Sem teto de custo em moeda; rate limiting e medicao permanecem | DR-005 §3 |
| Retencao de 90 dias para conversa, inbox e tool-call | DR-005 §4 |
| WhatsApp como canal de envio; webhook de recepcao fora da API TiaNet | ADR-009, adendo de 2026-08-27 |
| Leituras seguem fora da trilha; tool-calls tem log proprio | ADR-002, adendo de 2026-08-27 |
| Topologia sem webhook publico na TiaNet | `contexto-externo.md` §2.2 |

As dez regras inviolaveis do copilot estao no backlog, §3. A que mais restringe
o desenho: **o copilot nunca calcula dinheiro** — valores vem do Motor e o
agente repete campos tipados.

---

# 3. Escopo mapeado

| Fase | Entrega | Depende de LLM? |
|---|---|---|
| 0 | Validar canal, congelar governanca, prontidao de producao | nao |
| A | Resumo diario ao Credor e vespera ao Devedor | **nao** — texto montado em codigo |
| B | Identidade do copilot, RBAC segregado, autoria na trilha | nao |
| C | Conversa de leitura com tool-use restrito a GETs | sim |
| D | Pre-cadastro conversacional com aprovacao humana | sim |

---

# 4. API

Endpoints publicados por este plano. Os demais itens nao alteram o contrato
publico; quando alterarem, entram aqui antes da implementacao.

- `POST /iam/usuarios` - cria Usuario no Tenant do solicitante, ja com
  credencial definida e estado ativo; exige a permissao `usuario.criar` e
  `Idempotency-Key`. E-mail repetido responde 409 sem ecoar o endereco, e
  segredo fora da politica minima do dominio responde 422 sem ecoar o segredo.

- `GET /credit/devedores/{devedor_id}/saldo` - soma no Motor o saldo dos
  emprestimos **ativos** do Devedor na data de referencia; exige
  `motor.saldo.ler`. Devolve o total oficial e os itens por emprestimo, para
  conferencia da origem — nao para o consumidor recalcular. Devedor sem
  emprestimo responde zero explicito, nao 404.

Preparacao administrativa local anterior ao IMP-356, sem inferencia, webhook ou
dados de clientes:

- `GET /platform/openai/conexao` — snapshot local da conexao;
- `GET /platform/openai/diagnostico` — atualizacao explicita e limitada de
  plano, modelos e janelas de uso;
- `POST /platform/openai/conexao/login` — inicia device code, isento de
  `Idempotency-Key` pela ADR-020;
- `DELETE /platform/openai/conexao` — logout local com `Idempotency-Key`.

As duas leituras exigem `openai.conexao.ler`; as escritas exigem
`openai.conexao.gerir`. Essas rotas nao contam como execucao do IMP-356 e nao
alteram suas dependencias.

Alteracao de permissao sem endpoint novo, no mesmo ciclo:
`POST /credit/propostas-comerciais/{proposta_id}/enviar-para-analise` passou a
exigir `comercial.proposta.submeter` em vez de `comercial.proposta.decidir`
(IMP-360). O caminho nao mudou; a autorizacao, sim.

---

# 5. Fora de escopo

Declarado no backlog, §10. Em resumo: escrita financeira por chat, aprovacao por
agente, proposta comercial pelo copilot no v1, memoria de longo prazo, RAG e
autonomia alem do reativo.

---

# 6. Gates

Execution Gates conforme o
`docs/governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md`:

| Gate | Conteudo | Estado |
|---|---|---|
| GATE-E1a | governanca (IMP-358) | **cumprido** em 2026-08-27 |
| GATE-E1b | canal validado e producao pronta (IMP-352, IMP-359) | **parcial** — IMP-352 cumprido em 2026-08-31, com o canal validado contra o servidor real. Resta o IMP-359, e o insumo de **servidor** deixou de ser bloqueio: a VPS e o dominio existem. OpenRouter foi escolhido como rota proposta do piloto, sujeito à certificacao do modelo gratuito nominal, ZDR e politica de dados; `LLM_API_KEY` continua segredo operacional e nenhum valor entra no Git. O deploy foi sequenciado **depois** do PLAN-034 por decisao do fundador |
| GATE-E2 | Fase A e Fase B | em execucao |
| GATE-E3 | Fase C | nao iniciado |
| GATE-E4 | Fase D | nao iniciado |

O detalhe de cada gate, com condicao para seguir, esta no backlog §11.

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.2.0 | 2026-09-09 | Registra a preparacao administrativa local do Codex App Server e seus quatro endpoints; mantem IMP-359 e os gates do IMP-356. |
| 1.1.0 | 2026-09-09 | Reconcilia a aprovacao do catalogo B1 e da direcao de provedor: OpenRouter no piloto proposto, NVIDIA em comparacao sintetica e OmniRoute como gateway opcional condicionado. Gates operacionais permanecem abertos. |
| 1.0.0 | 2026-08-27 | Plano materializado a partir do backlog v1.5.0, com a secao API declarando `POST /iam/usuarios` do IMP-355. |
