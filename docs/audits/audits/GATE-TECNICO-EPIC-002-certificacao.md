# GATE Técnico — EPIC-002 (Cadastro de Devedores) — Certificação

**Versão:** 1.0.0
**Status:** Emitido
**Data:** 2026-08-08
**Emissor:** Engenharia (IMP-064)
**Destinatário:** Arquitetura
**Escopo:** EPIC-002 — implementação, testes, cobertura e migration

---

# 1. Parecer

> ## 🟢 EPIC-002 CERTIFICADO
>
> Todos os componentes da entrega possuem evidência verificável: domínio,
> aplicação, infraestrutura, API, integração, cobertura e migration.

Este GATE certifica o **software**, não o esforço (DA-099). Ele foi mantido
bloqueado durante toda a fase em que faltava evidência, e emitido apenas após a
última peça — o ciclo de migration exigido pela DA-002 — ser executada.

---

# 2. Componentes certificados

| Componente | Evidência | Estado |
|---|---|---|
| Domínio (Devedor, Contato, Documento, Unicidade, Eventos) | 100% de cobertura em `devedor.py`, `documento.py`, `contato.py`, `eventos_devedor.py`, `unicidade_devedor.py` | ✅ |
| Aplicação (5 casos de uso + histórico) | 24 testes de integração contra PostgreSQL real | ✅ |
| Infraestrutura (repositórios, UoW, idempotência, auditoria) | 13 testes de integração do repositório; auditoria e idempotência exercitadas | ✅ |
| API (7 endpoints) | 33 testes de contrato + 18 de integração | ✅ |
| Migration `0005` | ciclo DA-002 completo, 7/7 etapas | ✅ |
| Cobertura | 98% total; nenhum módulo do EPIC-002 abaixo de 94% | ✅ |
| Documentação | `docs:validate` 101 OK / 67 avisos / 0 erros | ✅ |

**Suíte total: 408 testes, 100% pass.**

---

# 3. Evidência da migration (DA-002)

Ciclo executado em banco dedicado (`mig_test`), separado do banco de testes —
a suíte executa `DROP TABLE ... CASCADE` no encerramento e contaminaria o ciclo.

| Etapa | Comando | Resultado observado |
|---|---|---|
| 1 | `DROP/CREATE DATABASE mig_test` | banco vazio |
| 2 | `alembic upgrade head` | 5 migrations, `0001` → `0005` |
| 3 | inspeção de `pg_constraint` | `uq_idempotency_key_chave_escopo :: UNIQUE (chave, escopo)`; constraint antiga ausente |
| 4 | `pytest` | 391 passed (contagem à época) |
| 5 | `alembic downgrade -1` | `UNIQUE (chave)` restaurada |
| 6 | `alembic upgrade head` | composta recriada |
| 7 | `pytest` | 391 passed |

## 3.1 Verificação comportamental (além da inspeção de schema)

Com dados reais no banco:

- duas linhas com a **mesma chave em escopos distintos**: **aceitas**;
- mesma chave no **mesmo escopo**: **rejeitada** — `duplicate key value violates
  unique constraint "uq_idempotency_key_chave_escopo"`.

Isto prova a correção da TASK-100 na camada de persistência, não apenas no ORM.

## 3.2 Ressalva do downgrade — confirmada na prática

O downgrade **falhou** na primeira execução, exatamente pelo cenário
documentado no cabeçalho da migration: linhas com a mesma chave em escopos
diferentes impedem restaurar `UNIQUE(chave)`. Após remover os duplicados, o
downgrade completou. A ressalva é real e permanece registrada no arquivo.

---

# 4. Defeitos encontrados durante a certificação

Os testes de integração da camada Application (IMP-061) revelaram **dois
defeitos de produção** que nenhuma camada anterior alcançava. Ambos corrigidos
antes desta emissão.

## 4.1 TASK-099 — Contatos órfãos (CRÍTICO)

**Sintoma:** atualizar os contatos de um Devedor acumulava em vez de substituir;
a leitura devolvia o contato removido.

**Causa:** `ContatoRepository` não possuía operação de remoção. O Aggregate
retirava o contato da coleção em memória e a persistência salvava apenas os
remanescentes — nada emitia `DELETE`. Não há `relationship` entre `DevedorORM` e
`ContatoORM`, logo não havia cascata.

**Correção:** `remove()` e `find_by_devedor()` acrescentados ao port e à
implementação; o caso de uso passou a reconciliar a coleção com o banco. O
comentário que afirmava falsamente existir cascata foi removido.

**Consequência para o domínio:** o estado persistido voltou a representar o
estado do Aggregate.

## 4.2 TASK-100 — Escopo de idempotência ignorado

**Sintoma:** cadastrar e depois inativar usando a mesma Idempotency-Key
respondia 409 indevido.

**Causa:** `find_by_chave` e `concluir` buscavam **apenas pela chave**. O campo
`escopo` era gravado por `registrar` e nunca lido. A tabela reforçava o defeito
com `UNIQUE(chave)`.

**Correção:** o par `(chave, escopo)` passou a ser a identidade em todas as
operações; migration `0005` alterou a constraint. Os quatro casos de uso e o
dublê `_FakeIdempotencia` foram alinhados — este último replicava o defeito,
razão pela qual os testes unitários não o detectavam.

**Regressão do EPIC-001:** verificada. Todos os testes de Tenant permanecem
verdes.

---

# 5. Cobertura (IMP-063)

**Total: 98%** (1818 statements, 28 não cobertos).

## 5.1 Módulos do EPIC-002

| Módulo | Cobertura |
|---|---|
| `domain/credit/devedor.py` | 100% |
| `domain/credit/documento.py` | 100% |
| `domain/credit/contato.py` | 100% |
| `domain/credit/eventos_devedor.py` | 100% |
| `domain/credit/unicidade_devedor.py` | 100% |
| `domain/credit/ports.py` | 100% |
| `application/consulta_devedor.py` | 100% |
| `application/historico_devedor.py` | 100% |
| `application/cadastro_devedor.py` | 99% |
| `application/atualizacao_devedor.py` | 99% |
| `application/estado_devedor.py` | 99% |
| `presentation/api/dependencies.py` | 100% |
| `presentation/api/devedores_routes.py` | 98% |
| `presentation/api/devedores_schemas.py` | 96% |
| `infrastructure/idempotencia.py` | 95% |
| `infrastructure/repositories/__init__.py` | 94% |

Nenhum módulo abaixo do critério de 90%.

## 5.2 Lacunas fechadas nesta fase

A medição inicial apontou `dependencies.py` em **77%** — as linhas não cobertas
eram os corpos dos *providers*, nunca executados porque todos os testes os
substituíam por dublês. Era lacuna real: um erro de fiação só apareceria em
produção. Foram cobertos por `test_dependencies_wiring.py`, que invoca os
providers de verdade e opera os serviços de ponta a ponta sem override.

Também foram cobertas, por serem alcançáveis e não defensivas:

- invariantes de nome na **criação** do Devedor (antes só testadas em `atualizar_nome`);
- `Documento.__eq__` contra outros tipos;
- validação direta de CPF sem passar por `from_str`;
- erro no **primeiro** dígito verificador (o teste existente exercitava só o segundo);
- limites de `Paginacao` (`pagina=0`, `tamanho=0`, `tamanho=101`);
- conflito de chave em andamento no cadastro.

## 5.3 Linhas remanescentes — justificativa nominal

As 28 linhas não cobertas são **guardas defensivas** contra estados que o fluxo
normal não produz:

| Local | Linha | Natureza |
|---|---|---|
| `cadastro/atualizacao/estado_devedor.py` | `raise IdempotenciaConflitoError("?", "resultado ausente no registro")` | registro concluído sem payload — inconsistência de banco |
| `infrastructure/idempotencia.py` | `raise` (re-raise de IntegrityError não-UNIQUE) | falha de integridade de outra natureza |
| `infrastructure/idempotencia.py` | `raise ... "registro inexistente"` | concluir chave que sumiu entre registrar e concluir |
| `devedores_routes.py` | `raise _nao_encontrado()` no histórico | Devedor desaparecido entre a dependência e o handler |
| `devedores_schemas.py` | `return valor` nos validators | ramo de valor não-string em campo tipado |
| `main.py` | `del exc` no handler 500 | descarte antes do log |
| `repositories/__init__.py` | ramos de filtro/None | combinações não exercitadas |

Nenhuma delas é alcançável sem simular corrupção de estado. Cobri-las exigiria
mocks que testariam o mock, não o código.

---

# 6. Validações finais

| Verificação | Resultado |
|---|---|
| `pytest` | **408 passed** |
| `pytest --cov` | **98%** |
| `black --check` | 79 arquivos, nenhuma alteração |
| `ruff check src tests` | 50 achados — **todos pré-existentes** (baseline era 63) |
| `mypy src` | 5 erros — **todos pré-existentes**, em módulos fora deste escopo |
| `docs:validate` | 101 OK, 67 avisos, **0 erros** |
| `docs:test` | 42/42 |
| Migration `0005` | ciclo 7/7 |

---

# 7. Ressalvas registradas

1. **`ruff` e `mypy` mantêm achados pré-existentes.** Comparados item a item com
   o baseline: nenhum introduzido por este trabalho. O `ruff` inclusive caiu de
   63 para 50 após a formatação.
2. ~~**Divergência de ordem entre serviços.**~~ **RESOLVIDA em 08/08/2026.** Os
   quatro casos de uso avaliam agora o **estado antes do hash**: se a operação
   anterior não terminou, esse é o fato dominante — um hash divergente durante
   operação em curso é sintoma, não causa. A AD-002 não fixa a ordem; a escolha
   foi por uniformidade de mensagem. Verificado nos quatro serviços; 408 testes
   verdes.
3. **Sem autenticação.** Nenhum endpoint valida tenant ou usuário. É o EPIC-006
   (IAM), classificado como pré-requisito de segurança no roadmap. O EPIC-002
   está certificado como funcionalidade, **não** como pronto para dado real.
4. **Isolamento multi-tenant parcial.** A pertinência Carteira↔Devedor é
   validada (ADR-018), mas não há verificação de que o Tenant é dono da Carteira
   — depende do IAM.

---

# 8. Rastreabilidade

| Item | Referência |
|---|---|
| Features | FEATURE-005, FEATURE-006, FEATURE-007, FEATURE-008 |
| User Stories | US-015 a US-027 (13) |
| IMPs | IMP-042 a IMP-064 |
| Decisões | ADR-018, AD-001, AD-002, ADR-002 |
| Comandos | DA-002 (certificação de migration), DA-099 (defeitos suspendem GATE) |
| Tasks corretivas | TASK-099, TASK-100 |

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Certificação do EPIC-002 — emitida após ciclo completo de migration (DA-002) e correção dos defeitos encontrados na certificação (DA-099). |
