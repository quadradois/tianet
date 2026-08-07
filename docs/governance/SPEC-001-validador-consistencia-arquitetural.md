# SPEC-001 — Validador de Consistência Arquitetural (docs:validate nível 2)

**Versão:** 1.1.0
**Status:** Aprovado
**Data:** 2026-08-07
**Autor:** Engenharia (TASK-090A — Discovery)
**Aprovação:** Arquitetura / 2026-08-07 (Architecture Review Board)
**Implementação:** TASK-090B

---

# 1. Objetivo

Especificar as verificações de **coerência semântica entre documentos** a serem
incorporadas ao `scripts/validate-docs.js`, elevando-o de validador estrutural a
guardião do contrato arquitetural.

O validador atual garante ID, estrutura, seções, links e referências cruzadas.
Não compara **conteúdo** entre documentos — lacuna que permitiu o PLAN-003 e o
PLAN-003-EXEC divergirem quanto ao contrato HTTP e passarem no congelamento
`256a99b` sem alarme, originando a DR-001 e a ADR-018.

---

# 2. Princípios de projeto

1. **Determinístico.** Regex e parsing estrutural. Sem IA, sem heurística
   probabilística, sem análise de linguagem natural. A mesma entrada produz
   sempre a mesma saída.
2. **Sem falso positivo silencioso.** Uma regra que não consegue decidir com
   segurança emite `[AVISO]`, nunca `[ERRO]`. Erro bloqueia commit; o custo de
   um falso erro é alto e corrói a confiança na ferramenta.
3. **Extração explícita, não adivinhada.** O validador lê seções declaradas
   (`# 6. API`), não o documento inteiro. Prosa que menciona uma rota não é
   declaração de contrato.
4. **Baseline preservada.** A adoção não pode transformar os 51 avisos atuais em
   erros nem introduzir erro em documento hoje válido.

---

# 3. Evidência levantada (TASK-090A)

O formato real dos artefatos foi inspecionado antes de definir as regras. Três
constatações determinam o desenho.

## 3.1 Placeholders são heterogêneos entre documento e código

| Origem | Placeholders observados |
|---|---|
| `docs/implementation/plans/*.md` | `{id}` (14), `{carteira_id}` (9), `{valor}` (2), `{cpf}` (1) |
| `src/emprestimo/presentation/api/*.py` | `{carteira_id}` (7), `{devedor_id}` (5), `{tenant_id}` (4) |

O plano escreve `/carteiras/{carteira_id}/devedores/{id}`; o código declara
`/carteiras/{carteira_id}/devedores/{devedor_id}`. **Comparação literal marcaria
todos os endpoints como divergentes.**

**Regra derivada — normalização obrigatória.** Antes de comparar, todo
`{qualquer_nome}` é reduzido a `{}`. Verificado: com essa normalização, PLAN-003
§6 e o código produzem conjuntos idênticos.

## 3.2 O prefixo do router não aparece no decorador

As rotas em `devedores_routes.py` são declaradas como `/carteiras/{}/devedores`,
e o prefixo `/credit` vive em `APIRouter(prefix="/credit")`. O plano escreve o
caminho completo.

**Regra derivada.** O extrator do código deve resolver `APIRouter(prefix=...)` e
concatená-lo a cada rota do arquivo. Sem isso, nada bate.

## 3.3 Nem toda crase contendo barra é um endpoint

Ocorrências reais no PLAN-003-EXEC que uma regra ingênua trataria como rota:

| Trecho | Linha | Natureza |
|---|---|---|
| `` `/reativar` `` | 221 | fragmento de frase (`…/inativar` e `/reativar`) |
| `` `/devedores/{id}` `` | 316 | histórico de versões — cita a rota **proibida** |

**Regra derivada.** Só é considerado endpoint o trecho que casa
`` `MÉTODO /caminho` `` (método HTTP explícito) **ou** que apareça em linha de
lista sob a seção de API declarada. Linhas de tabela de histórico de versões e
blocos `>` (nota/citação) são excluídos da extração.

---

# 4. Fase 1 — Coerência PLAN ↔ PLAN-EXEC (obrigatória)

## 4.1 Pareamento

`PLAN-00N` ↔ `PLAN-00N-execution-backlog`, pelo número. Plano sem backlog
correspondente (ou vice-versa) é `[AVISO]`, não erro — pode ser trabalho em
andamento.

## 4.2 Extração

| Artefato | Fonte | Escopo |
|---|---|---|
| PLAN | seção `# N. API` até o próximo `# ` | linhas de lista iniciadas por `- ` |
| PLAN-EXEC | blocos `## IMP-NNN` inteiros | campos `**Objetivo:**` e título |

Em ambos, extrai-se `(MÉTODO, caminho normalizado)`. Caminho sem método
explícito no backlog herda o método citado no mesmo item, se houver; não havendo,
o par entra como `(?, caminho)` e só participa da comparação de caminho.

## 4.3 Verificações

| # | Regra | Severidade |
|---|---|---|
| 1.1 | Caminho no backlog ausente do plano | **ERRO** |
| 1.2 | Mesmo recurso com forma estrutural distinta (ex.: aninhado no plano, plano no backlog) | **ERRO** |
| 1.3 | **Validação bidirecional:** o conjunto de endpoints do backlog deve ser igual ao do plano, não apenas contido nele | **ERRO** |
| 1.4 | Método divergente para o mesmo caminho | **ERRO** |
| 1.5 | IMP referencia US/FEATURE inexistente | AVISO (já coberto por referência cruzada) |

**Regra 1.3 (bidirecional).** Verifica `PLAN == EXEC`, não `PLAN ⊆ EXEC`. Um IMP
que implementa endpoint ausente do plano é tão grave quanto o inverso: significa
escopo entrando pela execução sem passar pelo planejamento. A direção
plano→backlog (endpoint planejado ainda sem IMP) permanece **AVISO**, pois
backlog incompleto é estado legítimo durante a execução.

**Regra 1.2 é a que teria barrado a DR-001.** Verificação: aplicada ao estado de
`256a99b`, o plano declarava `/credit/carteiras/{}/devedores/{}` e o backlog
`/devedores/{}` — mesmo recurso (`devedores`), formas estruturais distintas.

Mensagem esperada:

```
[ERRO] Contrato HTTP inconsistente para o recurso "devedores":
       PLAN-003 §6            : GET /credit/carteiras/{}/devedores/{}
       PLAN-003-EXEC IMP-058  : GET /devedores/{}
       O backlog de execução deve refletir o plano.
```

---

# 5. Fase 2 — Contrato PLAN ↔ implementação

## 5.1 Fonte da verdade do código

**Decisão a validar com a Arquitetura (ver §8, questão A).** Duas opções:

| Opção | Como | Prós | Contras |
|---|---|---|---|
| **A — AST/regex sobre os decoradores** | ler `@router.<verbo>("<caminho>")` + `APIRouter(prefix=)` | sem dependência de runtime; roda em qualquer máquina | reimplementa parcialmente o roteamento do FastAPI |
| **B — OpenAPI gerado** | subir o app e ler `/openapi.json` | fonte inequívoca, é o contrato real publicado | exige Python e dependências no passo de validação de docs (hoje só Node) |

**Recomendação da Engenharia: opção A.** O `docs:validate` roda no hook de
pre-commit e hoje não depende do ambiente Python; introduzir essa dependência
torna a validação de documentos refém do ambiente de execução da aplicação.

## 5.2 Verificações

| # | Regra | Severidade |
|---|---|---|
| 2.1 | Rota implementada ausente do PLAN | **ERRO** |
| 2.2 | Método divergente entre PLAN e implementação | **ERRO** |
| 2.3 | Rota no PLAN ainda não implementada | AVISO (backlog pendente é normal) |

---

# 6. Fase 3 — Códigos HTTP

## 6.1 Obstáculo identificado

Os códigos aparecem no PLAN em duas formas: inline por endpoint
(`(201; 404 carteira não encontrada; 409 …)`) e agregados em parágrafo
(`Padrões de erro: 400 payload_invalido / 404 …`). Não há forma canônica.

No código, os status vêm de três origens distintas: `status_code=` no decorador,
`HTTPException(status_code=…)` no handler, e os `add_exception_handler` de
`main.py` — este último mapeia exceção → status **fora** da rota.

## 6.2 Consequência para o escopo

Correlacionar código-fonte e documento aqui exige rastrear qual exceção cada
caso de uso levanta, o que é análise de fluxo, não parsing. **A Engenharia
recomenda limitar a Fase 3 à comparação PLAN ↔ PLAN-EXEC** (ambos texto,
mesma natureza), e tratar a comparação com a implementação como AVISO derivado
apenas dos códigos literais encontrados em `status_code=` e `HTTPException`.

| # | Regra | Severidade |
|---|---|---|
| 3.1 | Código citado no backlog ausente do plano para o mesmo endpoint | **ERRO** |
| 3.2 | Código literal no handler ausente do plano | AVISO |

---

# 7. Fase 4 — Domínio (posterior)

Escopo reduzido e determinístico:

| # | Regra | Severidade |
|---|---|---|
| 4.1 | PLAN cita Aggregate/Entity/VO/Evento cujo ID não existe em `docs/domain/` | AVISO |
| 4.2 | PLAN cita nome de Aggregate (ex.: "Carteira") sem DOMAIN correspondente | AVISO |

A regra 4.2 depende de um índice nome→ID que hoje não existe; sua construção é
pré-requisito e fica fora da TASK-090B.

---

# 8. Decisões da Arquitetura (Review Board, 2026-08-07)

As quatro questões abertas na v1.0 foram decididas. Todas confirmaram a
recomendação da Engenharia.

**A. Fonte da verdade do código (Fase 2) — parsing estático dos decoradores.**
OpenAPI gerado foi rejeitado como fonte primária: exigiria Node → Python →
FastAPI → import completo da aplicação apenas para validar documentos. Preserva-se
o princípio de que **governança documental não depende da aplicação estar
executável**. OpenAPI permanece admissível como validação complementar em CI,
nunca no pre-commit.

**B. Severidade — ERRO desde o primeiro dia, apenas para PLAN ↔ PLAN-EXEC.**
A regra tem evidência histórica (DR-001), não é hipótese: merece bloquear commit.
Regras futuras entram como AVISO até acumularem precedente.

**C. Placeholders — normalização automática, sem editar documentos.**
O nome do parâmetro pertence à implementação, não à identidade arquitetural. O
contrato é `GET /carteiras/{}/devedores/{}`; padronizar os documentos geraria
trabalho sem ganho arquitetural.

**D. Escopo da Fase 3 — limitado a PLAN ↔ PLAN-EXEC.** Sem análise de fluxo, sem
interpretação de Python, sem IA.

---

# 9. Entregáveis da TASK-090B

1. Novas verificações em `scripts/validate-docs.js`, agrupadas em bloco próprio
   e identificadas na saída como `[CONTRATO]`;
2. **Testes do próprio validador** — hoje inexistentes. Casos mínimos: divergência
   detectada, documentos coerentes, e cada caso-limite de §3.3;
3. Saída ampliada:

```
docs:validate
  ✓ Estrutura      ✓ IDs        ✓ Referências
  ✓ Contratos HTTP ✓ Plan × Backlog
```

4. Execução contra o estado atual do repositório com **0 erros** — a base já foi
   corrigida pela TASK-089; qualquer erro novo indica falso positivo a ajustar.

---

# 10. Critérios de aceitação (oficializados pela Arquitetura)

| ID | Critério |
|---|---|
| **CA-001** | O commit `256a99b` (estado anterior à TASK-089) **falha** obrigatoriamente — prova de que o validador teria evitado a DR-001 |
| **CA-002** | O `HEAD` atual **passa** |
| **CA-003** | Mudança apenas de placeholder (`{id}` ↔ `{devedor_id}`) **não** gera divergência |
| **CA-004** | Mudança de prefixo é **detectada** corretamente |
| **CA-005** | Rota citada apenas na seção de Histórico de Versões **não** gera falso positivo |
| **CA-006** | Trechos em crase que não representam endpoints (ex.: `` `/reativar` `` como fragmento de frase) são **ignorados** |
| **CA-007** | Cobertura de testes do próprio validador: **100% das regras implementadas** |

Adicionalmente: os 51 avisos de referência cruzada permanecem avisos, em mesmo
número — a adoção não pode alterar a baseline.

## 10.1 Estrutura de testes

O validador passa a ter poder de bloquear commits; portanto é software de
produção e exige proteção contra regressão:

```
scripts/
  validate-docs.js
  contract-check.js          # regras de contrato (Fases 1–3)
  tests/
    test-validator.js
    fixtures/
      plan-ok.md
      plan-divergente.md
      plan-exec-ok.md
      plan-exec-divergente.md
```

---

# 11. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Especificação inicial do validador de consistência arquitetural (TASK-090A). |
| 1.1.0 | 07/08/2026 | Aprovada pela Arquitetura: decisões A–D registradas, Regra 1.3 (validação bidirecional) acrescentada, critérios CA-001..CA-007 e estrutura de testes oficializados. |
