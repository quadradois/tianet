# 2026-09-02 (noite) - Handoff: a ADR-009 corrigida, a conexão do WhatsApp, e o que 19 rodadas de review ensinaram

**Versao:** 1.0.0

**Status:** PLAN-034 com **4 dos 7 itens**. O defeito operacional que o handoff
da manhã deixou aberto **foi corrigido**. Próximo item: IMP-368 (endpoints).

**Periodo coberto:** 2026-09-02, mesma data do handoff anterior — que este
substitui por ser mais recente, não por contradizê-lo.

**Base:** `origin/master`, três PRs mergeados no dia (#52, #53, e o do IMP-367).

**Substitui:** `2026-09-02-handoff-auditoria-documental-e-defeito-do-timeout.md`.
Aquele descreve a auditoria documental e continua valendo como registro dela; a
§3 dele **está resolvida** e é o item 1 abaixo.

---

# 1. O que fechou

| Item | O quê |
|---|---|
| PR #52 | Handoff da auditoria documental |
| PR #53 | **A violação da ADR-009** — retry sem prova de não aceite |
| IMP-367 | Casos de uso e permissões da conexão do WhatsApp |

## 1.1 — A ADR-009 (PR #53)

O adapter reenviava mensagem em três caminhos onde a ADR manda bloquear retry:
`5xx`, transporte indistinto, e `DecodingError` escapando para o Scheduler.

**A correção não foi uma lista maior, foi inverter o padrão.** Enumerar as
exceções "de depois do envio" falhou três vezes seguidas no review, porque o
critério não é observável — um `WriteError` pode estourar na primeira escrita,
sem nenhum byte na rede. O critério da ADR é a **prova**:

```
reenvia:  ConnectTimeout, ConnectError, PoolTimeout   (não chegou à rede)
resto:    resultado_desconhecido                       (5xx e DecodingError inclusos)
```

Escrito como allowlist, uma exceção nova do httpx cai no lado seguro sozinha.

## 1.2 — IMP-367

Três casos de uso (`Consultar`, `Conectar`, `Desconectar`), duas permissões
(catálogo em 57, versão 1.1.0), um port `ProvedorWhatsApp`, e a migration
`b58e3f21c4d7` — que também repara o `usuario.criar` do IMP-355, esquecido lá.

---

# 2. As duas descobertas que valem mais que o código

## 2.1 — O telefone da conta pareada existe

Eu concluí que não existia. **O fundador sabia que sim** — "nas instâncias do CRM
ele carrega o número conectado" — e a leitura ao vivo confirmou:

```
GET /instance/info/{id}   apikey: {tenant_key}   X-Tenant-ID: {tenant_id}
→ "jid": "556299999999:74@s.whatsapp.net"
```

**Por que eu não achei:** procurei no `/instance/status`, autenticado pela
*instância*. O `jid` está na rota autenticada por *Tenant*. Olhei um lado da
fronteira e concluí sobre os dois.

Registrado no contrato §4.4 com as três armadilhas, e a mais traiçoeira foi achada
por um teste meu escrito para outra coisa: **`@lid` também é só dígitos**.
Validar com `isdigit()` devolveria o identificador oculto como se fosse telefone.

## 2.2 — A instância já existe no provedor

`_garantir_instancia` lia "tabela local vazia" como "provedor vazio". No primeiro
`conectar` em produção criaria uma **segunda** instância — não pareada — enquanto
o WhatsApp do fundador continuava ligado na primeira. Tela pedindo QR para
sempre.

Corrigido com adoção: `/instance/all` devolve o token, então a plataforma adota a
`adm_tianet` existente. **Isso não sai de análise de código** — sai de saber o
que existe fora do repositório.

---

# 3. Caveats vigentes

Os do handoff da manhã continuam, menos o §4.8 (resolvido). Em resumo:

| # | Caveat |
|---|---|
| 3.1 | **Produção não existe.** VPS e domínio disponíveis; falta o IMP-359. Insumo externo pendente: o provedor de IA |
| 3.2 | Contrato declara política de senha mais frouxa que o sistema aceita |
| 3.3 | `scheduler_worker.py` em 69,91% |
| 3.4 | CPFs históricos em `audit_log` — decisão do fundador |
| 3.5 | `CLAUDE.md` da raiz é gitignored |
| 3.6 | Guardrail da ADR-003 casa por texto, não por ideia (4 linhas em `ADR-001`, `AMP-001`, `PLAN-001`) |
| 3.7 | Suíte Playwright deixa servidor órfão |
| 3.8 | **NOVO** — a auditoria da sincronização é escrita depois do commit, que já soltou o lock: dois pollings simultâneos podem gravar fora de ordem. Nomeado no código; single-tenant com um operador torna raro |
| 3.9 | **NOVO** — `criar_instancia` cuja resposta se perde ainda deixa órfã. Mitigado pela adoção: a próxima tentativa encontra e adota |

---

# 4. O que 19 rodadas de review ensinaram

O IMP-367 levou **19 rodadas do Codex**. Cada uma achou algo real. Mas o padrão
importa mais que a contagem.

**Uma família só, dezenove vezes.** Quase todos os achados eram: *efeito externo
acontecendo antes de haver garantia de registrá-lo*. Cifra resolvida tarde demais,
criação concorrente, nome validado depois, QR pendente virando erro, instância
órfã. Ver a família na terceira rodada teria poupado dez — e o jeito de ver era
perguntar "o que este código faz lá fora antes de conseguir escrever aqui?", não
esperar o revisor apontar mais um caso.

**Consertar cria defeito novo.** Três rodadas seguidas corrigiram o mesmo evento
de auditoria, e duas delas corrigiam a correção anterior. O lock que adicionei
não trancava nada — estava depois da leitura. A tradução de exceção que
adicionei nunca disparava — faltava no outro caso de uso. Mexer em ordem de
efeitos abre janelas onde não havia.

**Evento de rollback é uma afirmação sobre o mundo, não um log.** Numa trilha
append-only ele não se retira. Escrevi `rollback_aplicado` em dois lugares onde
era mentira: depois do commit, e depois de um logout que o provedor já aceitara.
Daí saíram três vocabulários para três situações — rollback (o estado voltou),
divergência (o efeito externo ficou), falha (deu errado, sem afirmar estado).

**Um guardrail escrito à mão falha do jeito que ele mesmo descreve.** O do
IMP-350 dizia, no próprio docstring: *"o defeito não era o esquecimento: era
depender de cada chamador lembrar de um remendo"* — e mantinha os status numa
lista escrita à mão. Meus três status novos não entraram, e um deles tinha **46
caracteres contra uma coluna de 40**. O teste passava verde. Reescrito para varrer
o código por AST, ele pegou o defeito na primeira execução.

**E o retorno cai.** As últimas quatro rodadas foram variações cada vez mais
estreitas do mesmo princípio. Vale um critério de parada explícito: quando duas
rodadas seguidas só produzirem P2 sobre código que a rodada anterior escreveu, o
loop está se alimentando de si mesmo — feche o item e registre o resto como
caveat.

---

# 5. Fluxo de trabalho vigente

```
commit local  →  review do Codex até aprovar  →  abre PR  →  Claude merga  →  CI  →  próximo
```

**O review vem ANTES do PR.** **Verificar o commit de MERGE, não os checks do
PR** — são commits diferentes.

---

# 6. Próximo ciclo

1. **IMP-368** — endpoints e contrato. Herda três decisões já tomadas: a
   `Idempotency-Key` fica de fora (PLAN-034 §3.1, com o porquê), o RBAC usa as
   duas permissões novas, e o DTO já tem `numero`, `nome_exibicao` e
   `qrcode_base64`;
2. **IMP-369** — a tela. O critério "número visível quando pareado" **agora tem
   fonte** (§2.1);
3. **IMP-370** — worker lê o token do repositório;
4. **IMP-359 — deploy.** Ponto de parada acordado.

Menores: o guardrail da ADR-003 (§3.6), limpeza de portas no pre-push (§3.7), e
as decisões sobre CPFs históricos (§3.4) e o `CLAUDE.md` (§3.5).

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-09-02 | A violação da ADR-009 corrigida com allowlist em vez de enumeração; o IMP-367 entregue com adoção de instância existente e o telefone da conta pareada localizado no `jid` — descoberta que veio do fundador, não do código; e o que 19 rodadas de review ensinaram, incluindo um guardrail que falhou exatamente do jeito que seu próprio docstring descrevia. |
