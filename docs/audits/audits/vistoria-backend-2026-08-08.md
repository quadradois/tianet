# Vistoria de Reconhecimento do Backend

**Data:** 2026-08-08
**Escopo:** reconhecimento do projeto `emprestimo` e levantamento do que falta para concluir o servico de backend.
**Resultado:** backend com EPIC-001 e EPIC-002 amplamente modelados e implementados, mas **nao concluido no estado atual do worktree**, porque a suite nao coleta por erro de sintaxe e ha divergencia entre ORM e migration.

---

## 1. Resumo executivo

O projeto tem uma base backend madura para um MVP: FastAPI, SQLAlchemy, Alembic, Pydantic, camadas separadas (`domain`, `application`, `infrastructure`, `presentation`), testes unitarios/integracao/API e uma documentacao de produto/arquitetura bem estruturada.

O EPIC-002 (Cadastro de Devedores) aparece certificado nos documentos oficiais, com endpoints, services, repositorios, eventos, idempotencia e auditoria. No entanto, a verificacao executada nesta vistoria mostra que o estado atual do codigo nao sustenta essa certificacao: `uv run pytest` falha ainda na coleta, `ruff` acusa 158 problemas e `mypy` para no mesmo erro de sintaxe.

Conclusao pratica: o backend esta proximo em termos de desenho e cobertura planejada, mas antes de considerar o servico concluido e pronto para continuidade, e necessario estabilizar o worktree, corrigir a sintaxe quebrada, alinhar migration/ORM e refazer os gates tecnicos.

---

## 2. Evidencias observadas

### Estrutura e stack

- `pyproject.toml` define Python `>=3.12` e dependencias principais: FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic e psycopg.
- A estrutura encontrada em `src/emprestimo` segue camadas:
  - `domain`: regras de negocio e entidades de Platform/Credit.
  - `application`: casos de uso e ports transacionais.
  - `infrastructure`: ORM, repositorios, auditoria, idempotencia e Unit of Work.
  - `presentation/api`: FastAPI, rotas, schemas e dependencies.
- `migrations/versions` possui migrations ate `0005_idempotency_key_escopo.py`.
- `tests` contem testes unitarios, integracao de application/repositorios e API.

### Documentacao oficial

- `docs/implementation/plans/PLAN-003-epic-002-cadastro-de-devedores.md` define o contrato do EPIC-002: Devedor, Contato, Documento, unicidade, eventos, repositorios, services, API e migration.
- `docs/implementation/backlogs/PLAN-003-execution-backlog.md` decompoe o trabalho em IMP-042..IMP-064.
- `docs/audits/audits/GATE-TECNICO-EPIC-002-certificacao.md` declara EPIC-002 certificado, suite total de 408 testes verdes e cobertura total de 98%.
- A mesma certificacao registra ressalva relevante: endpoints sem autenticacao e isolamento multi-tenant completo dependem do EPIC-006/IAM.

### Codigo implementado

- `src/emprestimo/presentation/api/main.py` inclui `devedores_router` no app FastAPI.
- `src/emprestimo/presentation/api/devedores_routes.py` implementa rotas sob `/credit/carteiras/{carteira_id}/devedores`, incluindo criar, consultar/listar, atualizar, inativar, reativar e historico.
- `src/emprestimo/presentation/api/dependencies.py` monta services de Devedor e centraliza `get_devedor_da_carteira`, validando pertinencia Carteira-Devedor.
- `src/emprestimo/infrastructure/unit_of_work.py` expoe `tenant`, `usuario`, `configuracao`, `carteira`, `devedor`, `contato` e `idempotencia`.
- `src/emprestimo/infrastructure/repositories/__init__.py` implementa repositorios SQLAlchemy para Tenant, Usuario, Configuracao, Carteira, Devedor e Contato.

### Verificacoes executadas

| Comando | Resultado |
|---|---|
| `uv run pytest` | Falhou na coleta com 16 erros causados por `SyntaxError` em `src/emprestimo/domain/credit/devedor.py:274` |
| `uv run ruff check src tests` | Falhou com 158 erros, incluindo o mesmo erro de sintaxe, imports/linhas longas e `pytest` indefinido em `tests/unit/domain/test_usuario.py` |
| `uv run mypy src` | Falhou com 1 erro de sintaxe em `src/emprestimo/domain/credit/devedor.py:274` |
| `npm run docs:validate` | Passou: 132 OK, 47 avisos, 0 erros |

---

## 3. Achados principais

### A1. O backend nao esta executavel no estado atual

O arquivo `src/emprestimo/domain/credit/devedor.py` tem uma string tripla aberta indevidamente em `remover_contato`.

Trecho observado:

```python
def remover_contato(self, contato_id: uuid.UUID) -> None:
    ...
    self._verificar_ativo()
    """
    contato = self._buscar_contato(contato_id)
    contato.remover()
    self._marcar_atualizado()
```

Esse `"""` transforma o corpo real do metodo em string aberta e faz o parser quebrar mais adiante, reportando `SyntaxError` na docstring de `_verificar_ativo`.

Impacto: a aplicacao nao importa, os testes nao coletam e qualquer afirmacao de backend concluido fica suspensa ate essa correcao.

### A2. Ha divergencia entre ORM e migration para `contato.removido_em`

O ORM atual tem:

```python
removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Mas `migrations/versions/0004_devedor_contato.py` nao cria a coluna `removido_em` na tabela `contato`. A migration `0005` trata idempotencia, nao esse campo.

Impacto: mesmo depois de corrigir a sintaxe, um banco criado via Alembic tende a nao possuir a coluna exigida pelo ORM/repositorio. Operacoes que persistem ou leem Contato podem falhar em runtime.

### A3. Soft-delete de Contato esta em transicao e precisa ser fechado

O codigo atual aponta que `remove()` fisico foi retirado e que Contato deve ser removido por soft-delete (`Contato.remover()` + `removido_em`). Os testes tambem referenciam `removido_em`.

Porem, alem da migration ausente, o metodo `Devedor.remover_contato` esta quebrado exatamente na regiao que deveria aplicar o soft-delete.

Impacto: a regra de preservacao historica de Contato nao esta comprovada no estado atual.

### A4. Autenticacao, autorizacao e isolamento por Tenant ainda nao fecham seguranca de producao

Os endpoints de Devedor validam pertinencia entre `carteira_id` da URL e o `devedor_id` carregado, mas nao ha evidencia de validacao de token, Principal, Tenant do usuario ou RBAC na API atual.

Isto bate com as ressalvas da documentacao:

- `GATE-TECNICO-EPIC-002-certificacao.md` registra "Sem autenticacao" e "Isolamento multi-tenant parcial".
- `ADR-004-autenticacao-e-autorizacao-iam.md` coloca IAM no EPIC-006 e define que endpoints protegidos devem responder 401 sem token.

Impacto: funcionalmente o cadastro pode estar desenhado, mas nao deve ser tratado como pronto para dados reais expostos fora de ambiente controlado.

### A5. Qualidade automatizada esta abaixo do gate declarado

O gate tecnico documentado afirma `ruff`, `black`, `mypy`, cobertura e testes verdes. A vistoria atual observou:

- `pytest` bloqueado por sintaxe.
- `mypy` bloqueado por sintaxe.
- `ruff` com 158 achados.
- `docs:validate` verde, com avisos.

Impacto: o proximo passo nao e desenvolver feature nova; e restaurar o estado verificavel.

### A6. Worktree esta sujo antes desta vistoria

Antes da criacao deste documento, `git status --short` ja indicava alteracoes em:

- `docs/domain/credit/aggregates/DOMAIN-020-aggregate-devedor.md`
- `src/emprestimo/application/atualizacao_devedor.py`
- `src/emprestimo/domain/credit/contato.py`
- `src/emprestimo/domain/credit/devedor.py`
- `src/emprestimo/domain/credit/ports.py`
- `src/emprestimo/domain/platform/usuario.py`
- `src/emprestimo/infrastructure/db/orm.py`
- `src/emprestimo/infrastructure/repositories/__init__.py`
- `tests/unit/domain/test_contato.py`
- `tests/unit/domain/test_devedor.py`
- `tests/unit/domain/test_usuario.py`

Impacto: parte dos achados pode vir de trabalho em andamento. Antes de fechar backend, e preciso decidir se essas alteracoes entram no escopo oficial ou se serao separadas/revisadas.

---

## 4. O que falta para concluir o backend

### Prioridade 0: restaurar executabilidade

1. Corrigir `src/emprestimo/domain/credit/devedor.py` removendo a string tripla indevida e reativando o corpo de `remover_contato`.
2. Rodar `python -m py_compile` ou `uv run pytest tests/unit/domain/test_devedor.py` para confirmar que o modulo importa.
3. Rodar `uv run pytest` novamente para revelar falhas reais depois da coleta.

### Prioridade 1: alinhar persistencia com dominio atual

1. Decidir formalmente se `Contato` usa soft-delete com `removido_em`.
2. Se sim, criar migration Alembic aditiva para adicionar `contato.removido_em`.
3. Ajustar/validar downgrade.
4. Executar ciclo de migration: `alembic upgrade head`, testes, `alembic downgrade -1`, `alembic upgrade head`.

### Prioridade 2: fechar o gate tecnico real

1. Corrigir os erros de `ruff` introduzidos ou atualmente ativos no escopo.
2. Rodar `uv run mypy src` depois da sintaxe corrigida e tratar os erros restantes.
3. Rodar suite completa: `uv run pytest`.
4. Rodar cobertura se o gate continuar exigindo 90%+ nos modulos novos.
5. Manter `npm run docs:validate` verde.

### Prioridade 3: reconciliar documento de certificacao com estado atual

1. Atualizar ou suspender temporariamente o GATE tecnico do EPIC-002 se o codigo continuar quebrado.
2. Registrar uma nova nota de retificacao quando os comandos voltarem a passar.
3. Evitar declarar "408 testes verdes" enquanto a suite atual falha na coleta.

### Prioridade 4: tratar seguranca como pre-requisito antes de producao

1. Implementar EPIC-006/IAM ou, no minimo, documentar explicitamente que a API e interna/protegida por infraestrutura externa ate o IAM.
2. Adicionar teste de contrato para endpoints protegidos: sem token deve responder 401, exceto `/health`.
3. Resolver Principal/Tenant a partir do token e usar isso como fonte de isolamento, nao apenas `carteira_id` vindo da URL.

---

## 5. Recomendacao de sequencia

1. **Consertar a sintaxe de `devedor.py`** e rodar a suite para obter o mapa real de falhas.
2. **Fechar a mudanca de soft-delete de Contato** com migration e testes de repositorio/application.
3. **Limpar gates locais** (`pytest`, `ruff`, `mypy`, `docs:validate`) antes de qualquer feature nova.
4. **Emitir retificacao do gate tecnico** com comandos reais observados.
5. **Seguir para EPIC-006/IAM** antes de tratar o backend como pronto para dados reais ou ambiente exposto.

---

## 6. Parecer final

O backend tem uma arquitetura consistente e um volume expressivo de implementacao ja presente, mas **na vistoria de 2026-08-08 ele nao esta concluido**. O bloqueio imediato e tecnico: o codigo nao importa por erro de sintaxe. O segundo bloqueio e estrutural: o modelo de soft-delete de Contato exige alinhar dominio, ORM, repositorio, migration e testes.

Depois desses ajustes, a conclusao do servico deve ser julgada apenas por verificacao observada: suite completa verde, `ruff` e `mypy` limpos ou com baseline formal, migrations validadas e documentacao de gate atualizada.
