# 2026-09-03 — Handoff: IMP-368 fechado, SPEC-003, e o gate que o review não substitui

**Versao:** 1.0.0

**Status:** PLAN-034 com **5 dos 7 itens**. Próximo: IMP-369 (tela).

**Periodo coberto:** 2026-09-03.

**Base:** `origin/master` em `71d4ab6` (merge do PR #57), CI verde sobre o
commit de merge.

**Substitui:** `2026-09-02-handoff-adr-009-corrigida-e-conexao-do-whatsapp.md`.

---

# 1. O que fechou

| Item | O quê |
|---|---|
| **IMP-368** | As quatro operações da conexão de WhatsApp. PR #57, três rodadas de review |
| **SPEC-003** | Gate de pré-voo: consultar o grafo antes de alteração arquitetural |
| **ADR-019** | Isenção de `Idempotency-Key` promovida de plano a decisão arquitetural |
| **Ambiente** | `pytest` na máquina passa a ler o `.env`. Destrava rodar a suíte |

Inventário da API: **107 → 111 operações**.

---

# 2. O erro que eu cometi, e que custou seis documentos

O `GET /platform/whatsapp/conexao` buscava o QR **no provedor** a cada chamada.
A tela faz polling de status enquanto o pareamento não fecha, então era uma ida
externa por pergunta "já conectou?", na rota mais chamada do recurso. **Tirar
isso está certo, e o motivo é esse: custo de chamada.**

**Não foi o motivo que escrevi.** O revisor classificou como *escalada de
privilégio* — o QR saía sob `whatsapp.conexao.ler` e permitiria a um usuário
somente-leitura alterar a conexão. Aceitei o rótulo e o escrevi em seis
documentos, incluindo este handoff e o corpo do PR #57.

**Esse usuário não existe.** A [ADR-003](../../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md)
§60 fixa, desde 2026-09-01, que a TiaNet tem **um operador humano**, com todas as
permissões. Não há de quem escalar. As permissões `whatsapp.conexao.ler` e
`.gerir` não protegem ninguém hoje — são preparação, não proteção.

**A ADR estava ao meu alcance e eu não a li até o fim.** Li "single-tenant, um
operador", inventei um cenário de perfil restrito que a própria ADR descarta, e
tratei o rótulo do revisor como verificação em vez de hipótese. O fundador
apontou em 2026-09-03; a correção passou por PLAN-034, o backlog do IMP-369, a
SPEC-004, dois docstrings de código e dois testes.

**A lição, e ela vale mais que o conserto:** *um revisor aponta o que vê no
código; ele não sabe quantas pessoas usam o sistema.* Rótulo de severidade —
"bloqueante", "escalada de privilégio" — é hipótese a verificar contra o
domínio, não conclusão a repetir. E quando o desenho pressupõe um ator, a
pergunta antes de escrever é simples: **esse ator existe?**

**O que sobreviveu:** o código, o guardrail (que conta a **chamada**, não o
campo) e o cenário do teste — pareamento **pendente**, o único estado em que
havia QR a buscar.

---

# 3. As três descobertas que não saem de análise de código

## 3.1 — `/CLAUDE.md` está no `.gitignore`

Linha 43. **As regras normativas do projeto vivem em arquivo não versionado.**
Um clone limpo não as tem; emenda feita nelas não viaja para máquina nenhuma.

Isso deixou de ser curiosidade quando o review classificou como **bloqueante**
uma violação da regra 3 do `CLAUDE.md`. Corrigir a regra lá teria sido conserto
local e invisível — foi por isso que a exceção virou a ADR-019, versionada.

**Vale decidir se este arquivo deve ser versionado.** Enquanto não for, toda
regra que ele carrega é combinada de máquina, não do repositório.

## 3.2 — O AMP-001 não registrava a ADR-018

O Identifier Registry declara que o AMP-001 é *"a única fonte de verdade"* para
numerar ADR, e manda **não** usar `ultimo+1`. Consultei, e a tabela parava no
017 — a ADR-018, emitida em 07/08, não estava lá. Quem escolhesse por ali pegaria
`018` de novo: a colisão que a SPEC-002 §5.2 existe para impedir.

Criada a seção "Emitidas fora da reserva", com 018 e 019.

## 3.3 — Review adversarial e gate de CI acham coisas diferentes

Três rodadas de Codex **não** pegaram duas coisas que o gate de pre-push pegou na
primeira execução:

- **onze `no-untyped-def`** no arquivo de teste novo — porque eu verificava com
  `mypy src` (132 arquivos) e o gate roda `mypy src tests` (268);
- **o contador de superfície do BFF**, parado em 107 enquanto o snapshot foi a
  111. Errado **desde os commits originais do IMP-368**, não das correções.

O revisor roda testes direcionados; o gate roda tudo. **Um não substitui o
outro**, e declarar "verde" com base no escopo estreito foi impreciso.

---

# 4. Caveats vigentes

Os do handoff de 02/09 continuam, com estes movimentos:

| # | Caveat | Estado |
|---|---|---|
| 3.1 | **Produção não existe** — falta o IMP-359 | **Desbloqueado**: o provedor de IA foi escolhido e a chave existe. Nenhum insumo externo trava mais |
| 3.5 | `CLAUDE.md` da raiz é gitignored | **Agravado** — ver §3.1 acima. Custou um bloqueante de review |
| 3.7 | Suíte Playwright deixa servidor órfão | **Confirmado na prática**: três tentativas de push falharam por porta 3107/3207 presa, nenhuma por código |
| — | **NOVO** — `pytest` na máquina não lia o `.env` | **Resolvido**. `database_url()` resolve por ambiente → `.env` → derivação da `POSTGRES_PASSWORD` |
| — | **NOVO** — convergência do `logout` no Evolution | **Não certificada, e nenhum review fecha.** Ver §5 |

Seguem abertos sem mudança: 3.2 (política de senha), 3.3 (`scheduler_worker` em
69,91%), 3.4 (CPFs em `audit_log`), 3.6 (guardrail da ADR-003 casa por texto),
3.8 e 3.9 (janelas de efeito externo).

---

# 5. O que só produção responde

**Ninguém mediu o que o Evolution responde a um `logout` repetido.** O lado da
TiaNet converge — `desparear()` sobre conexão já despareada é no-op, coberto por
teste. Mas o adapter recusa qualquer resposta não-2xx, então se o provedor tratar
o caso como erro, a segunda chamada falha em vez de convergir.

**Não há ambiente de teste do Evolution** (`contexto-externo` §2.1). A verificação
só existe em produção, com o número do fundador — o mesmo caminho da validação de
2026-08-31.

Está declarado como **premissa, não como fato**, na ADR-019, no docstring das
rotas e na isenção do guardrail. O revisor não o considerou pendência para merge.
Entra na validação do IMP-359.

**Segunda pendência operacional:** a instância `adm_tianet` deve ser **apagada**
no provedor antes do primeiro `conectar` valer como definitivo. O nome passou a
ser `tianet_{tenant_id}`, então a adoção não a encontra e ela vira sessão morta
permanente — o acúmulo que o fundador pediu para evitar.

---

# 6. O SPEC-003, e a prova de que não é teatro

O gate exige, antes de alteração arquitetural: verificar se o grafo está fresco,
consultar as cinco dimensões, e produzir um bloco de saída com o campo **`Achado
que mudou o desenho`** — que existe para tornar o gate falsificável.

**Aplicado no próprio ciclo que o criou, e deu `SIM`:** o revisor pediu correção
no contrato; o pré-voo mostrou que a correção certa era no caminho de leitura.

Duas defesas do documento foram medidas, não supostas:

- **Passo 0.** O grafo estava congelado havia 13 dias, escondendo 12 módulos
  novos de `src/` — `cifra.py`, `conexao_whatsapp.py` (domínio e aplicação),
  `whatsapp_routes.py`. Exatamente segurança, persistência e API.
- **Truncamento.** A primeira consulta real achou 352 nós e exibiu 57. Quem lê
  16% e conclui reproduz o erro de 2026-08-22 com ferramenta nova.

O grafo foi atualizado e passou a **cobrir documentos**: 10.768 nós, 25.809
arestas, 1.118 arquivos. Uma consulta hoje devolve DR-006, PLAN-034 §4.2 e
ADR-009 ao lado de `EvolutionTenantClient`.

---

# 7. O que quatro rodadas de review ensinaram

**A quarta cobrança da mesma coisa não é teimosia do revisor — é sinal de que o
registro está no lugar errado.** A §3.1 do PLAN-034 terminava dizendo: *"três
rodadas cobraram a chave; a decisão está aqui para que a quarta encontre a
resposta em vez da pergunta"*. A quarta cobrou assim mesmo, e classificou como
bloqueante. O raciocínio estava certo; o lugar estava errado. Exceção justificada
dentro de um backlog não é exceção à regra arquitetural — é **contradição entre
dois documentos**, e quem chega sem contexto lê a regra.

**Consertar cria defeito novo, de novo.** A rodada 2 achou que meu parser de
`.env` reintroduzia o próprio bug que ele existia para eliminar
(`senha # comentario` virava senha literal com o comentário dentro). E o achado
atrás do achado: meus testes trocavam a função de leitura por um lambda, então
validavam a precedência e **nunca a leitura** — que era onde o defeito estava.

**Recusar alto vence interpretar por conta.** A correção final do parser não foi
implementar a gramática completa do Compose: foi **recusar pelo nome** o que ele
não sabe ler. Divergir em silêncio é a classe de bug de toda esta saga.

**Nem toda cobrança do revisor procede, e vale verificar antes de ceder.** A
rodada 3 pediu `codigo` estável em `TokenConexaoIlegivelError`. `CarteiraNaoEncontradaError`
também mapeia para 404 e também não tem — só `ViolacaoInvarianteError` carrega.
Atender faria dela a exceção da exceção. A saída foi **formalizar a convenção**
em código versionado.

---

# 8. Fluxo de trabalho vigente

```
commit local  →  review do Codex até aprovar  →  abre PR  →  merge  →  CI  →  próximo
```

**O review vem ANTES do PR.** **Verificar o commit de MERGE, não os checks do
PR** — são commits diferentes.

**Acrescentar:** rodar o gate de pre-push é parte de "verificar", não formalidade
de push. Ele achou o que três rodadas de review não acharam.

---

# 9. Próximo ciclo

1. **IMP-369 — a tela.** Herda o desenho: polling de status no `GET`, barato; o
   QR vem do `POST`, pedido uma vez quando o operador quer parear;
2. **IMP-370** — worker lê o token do repositório;
3. **IMP-359 — deploy.** Sem insumo externo pendente. Inclui a validação do
   `logout` repetido (§5) e apagar a `adm_tianet`;
4. **Mercado Pago** — depois do deploy. `contexto-externo` §2.4 registra o fluxo
   (devedor paga o Credor) e as duas colisões nomeadas.

Menores: decidir se `/CLAUDE.md` deve ser versionado (§3.1), limpeza de portas no
pre-push (§4), e as pendências antigas 3.2, 3.3, 3.4, 3.6.

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-09-03 | IMP-368 fechado. O QR era buscado no provedor a cada consulta, não só exposto no DTO, e sair dali economiza uma chamada externa por polling. Registrado também o erro de percurso: aceitei do revisor o rótulo "escalada de privilégio" sem verificar que a ADR-003 fixa um operador humano único — o usuário somente-leitura que eu descrevi não existe, e a correção alcançou seis documentos. Três descobertas que nenhuma análise de código encontra: `/CLAUDE.md` é gitignored e por isso a exceção virou ADR-019; o AMP-001 não registrava a ADR-018, e a fonte de verdade da numeração levaria à colisão que a SPEC-002 existe para impedir; e o gate de pre-push achou dois defeitos que três rodadas de review adversarial não acharam. SPEC-003 criado e aplicado no próprio ciclo, com `Achado que mudou o desenho` = SIM. |
