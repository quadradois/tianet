# PLAN-027-EXEC - Backlog do Wizard de Lancamento

**ID:** PLAN-027-EXEC

**Versao:** 1.1.0

**Status:** IMP-305 concluido; IMP-306..311 planejados

---

# 1. Contexto

Ordem executavel do PLAN-027. A numeracao continua apos IMP-304, ultimo item do
PLAN-025.

O ciclo materializa o caminho unico de lancamento: uma operacao de backend
atomica, o wizard que a consome e as duas telas de leitura pedidas pelo Credor.
Nada e removido — as telas passo a passo continuam alcancaveis, e a Proposta com
aprovacao permanece porque e a caixa de entrada do agente de IA
(`FOUNDATION-001 §3.1`).

---

# 2. Fase A - Backend

### IMP-305 - Servico de lancamento composto

- **Objetivo:** servico de aplicacao que, sob um unico `UnitOfWork`, resolve ou
  cria o Devedor, percorre Proposta e Contrato pelos metodos de agregado, cria o
  Emprestimo e gera o plano de parcelas, com um commit unico.
- **Componentes afetados:** `src/emprestimo/application/lancamento.py`,
  `tests/integration/application/test_lancamento.py`.
- **Dependencias:** nenhuma.
- **Criterios de conclusao:** invariantes executadas pelos metodos de agregado
  com `usuario_id`, nunca contornadas; trilha de auditoria completa; falha em
  qualquer passo desfaz tudo; nenhum calculo financeiro fora do Motor.
- **Suite minima:** integracao contra PostgreSQL real, com rollback exercitado
  passo a passo.
- **Status:** Concluido.
- **Nota de execucao:** o guardrail de exclusividade do Motor
  (`test_motor_exclusivity_guardrails.py`) proibe qualquer modulo fora do Motor
  de importar `motor_financeiro`. O orquestrador recebe a etapa financeira por
  injecao (`CriadorDeEmprestimo`) e nao referencia o Motor em nenhum ponto; a
  criacao do Emprestimo e a geracao do plano vivem em
  `application/motor_financeiro.criar_emprestimo_e_plano_em`, que aceita um
  `UnitOfWork` ja aberto.

### IMP-306 - Endpoint de lancamento

- **Objetivo:** expor a operacao em
  `POST /credit/carteiras/{carteira_id}/lancamentos`, com `Idempotency-Key`
  obrigatoria.
- **Componentes afetados:** `presentation/api/lancamento_routes.py`,
  `presentation/api/lancamento_schemas.py`, `presentation/api/main.py`,
  `presentation/api/openapi.py`, snapshot OpenAPI governado.
- **Dependencias:** IMP-305.
- **Criterios de conclusao:** replay com a mesma chave devolve o resultado
  original; payload divergente com a mesma chave e conflito; RBAC exige as
  permissoes de Devedor, Comercial, Contratos e Motor; contagem de operacoes do
  snapshot atualizada de forma explicita.
- **Suite minima:** integracao de API, contrato e idempotencia.
- **Status:** Planejado.

### IMP-307 - Comprovante do lancamento

- **Objetivo:** gerar no backend o texto do comprovante e enfileirar o envio
  fora da transacao do lancamento.
- **Componentes afetados:** `application/comprovante.py`,
  `domain/credit/operacao_diaria.py` (valor `whatsapp` em `CanalComunicacao`),
  migration aditiva.
- **Dependencias:** IMP-305.
- **Criterios de conclusao:** o texto usa somente valores retornados pelo Motor;
  o envio nao bloqueia o commit; falha de canal nao desfaz o lancamento.
- **Suite minima:** unidade da montagem do texto, integracao do enfileiramento.
- **Status:** Planejado.

---

# 3. Fase B - Frontend

### IMP-308 - Wizard de lancamento

- **Objetivo:** tres passos — Devedor, Condicoes, Confirmacao — com uma unica
  chamada ao endpoint.
- **Componentes afetados:** `frontend/src/app/app/lancamentos/`, componentes de
  wizard, camada BFF e cliente tipado.
- **Dependencias:** IMP-306.
- **Criterios de conclusao:** campos tipados, sem JSON cru; nenhum UUID digitado
  pelo operador; nenhuma aritmetica no frontend; erro preserva o que foi
  digitado e exibe o correlation ID.
- **Suite minima:** unidade, componente, BFF e Playwright.
- **Status:** Planejado.

### IMP-309 - Tela de emprestimos

- **Objetivo:** apresentar em andamento, quitados e encerrados a partir do
  estado oficial retornado pelo backend.
- **Componentes afetados:** `frontend/src/app/app/motor/`, componentes de
  listagem.
- **Dependencias:** nenhuma.
- **Criterios de conclusao:** nenhuma classificacao calculada no frontend;
  estados vazios explicitos.
- **Suite minima:** componente e Playwright.
- **Status:** Planejado.

### IMP-310 - Devedor com situacao do emprestimo

- **Objetivo:** o detalhe do Devedor passa a exibir os emprestimos dele.
- **Componentes afetados:** `frontend/src/app/app/devedores/[devedorId]/`.
- **Dependencias:** IMP-309.
- **Criterios de conclusao:** somente leitura; somente valores retornados.
- **Suite minima:** componente e Playwright.
- **Status:** Planejado.

---

# 4. Fase C - Certificacao

### IMP-311 - Jornada real e recertificacao

- **Objetivo:** cenario que preenche o wizard na interface contra FastAPI e
  PostgreSQL reais, ate o plano de parcelas.
- **Componentes afetados:** `frontend/tests/jornadas-e2e/`, matriz de
  rastreabilidade, relatorio do ciclo.
- **Dependencias:** IMP-308, IMP-309, IMP-310.
- **Criterios de conclusao:** o cenario falha se a cadeia quebrar em qualquer
  ponto, verificado nos dois sentidos; gates completos verdes; matriz sem
  declarar jornada observada que nao se completa.
- **Suite minima:** gates completos do PLAN-027.
- **Status:** Planejado.

---

# 5. Gates

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate` com 0 erros e sem avisos novos;
- `npm run docs:test`;
- `node scripts/tests/test-plan-025-contracts.js`;
- `git diff --check`;
- frontend: typecheck, lint, unit, component, contract, BFF e build;
- Playwright de jornada real contra stack real;
- nenhum calculo financeiro fora do Motor e nenhum token no browser.

---

# 6. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-08-16 | IMP-305 concluido: lancamento composto em transacao unica, com a etapa financeira injetada para respeitar o guardrail de exclusividade do Motor. |
| 1.0.0 | 2026-08-16 | Backlog inicial IMP-305..IMP-311. |
