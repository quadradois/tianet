# PLAN-027 — Wizard de Lancamento de Emprestimo

**ID:** PLAN-027

**Versao:** 1.0.0

**Status:** Aprovado para execucao

**Discovery:** `docs/audits/discoveries/wizard-lancamento-discovery-sdd.md`

---

# 1. Objetivo

Materializar o caminho unico de lancamento aprovado no Discovery: uma operacao
de backend atomica e um wizard de tres passos, mais as duas telas de leitura que
o Credor pediu.

---

# 2. Decisoes formais

| # | Decisao | Fundamento |
|---|---|---|
| 1 | **Sem previa do plano antes de confirmar** | Exigiria endpoint de dry-run do Motor, superficie nova para ganho que o Credor ja controla — ele escolhe os quatro parametros. Adicionavel depois sem retrabalho. |
| 2 | **Contato WhatsApp obrigatorio no cadastro pelo wizard** | Sem numero nao ha destino para o comprovante. |
| 3 | **Terceiro grupo chamado "Encerrados"** | Cancelado e encerrado nao sao quitados nem estao em andamento. |
| 4 | **Endpoint `POST /credit/carteiras/{id}/lancamentos`** | `POST /credit/contratos/{id}/emprestimos` ja existe e significa outra coisa. |
| 5 | **Product reutilizado, sem novo EPIC** | Mesmo precedente do PLAN-025: o wizard e caminho novo para capacidade existente. |

---

# 3. Reutilizacao Product

| Familia | Decisao |
|---|---|
| PRODUCT-001..009 | reutilizar sem novo ID |
| EPIC-002..005 | reutilizar; o lancamento atravessa Cadastro, Comercial, Contratos e Motor |
| FEATURE, US | reutilizar; nenhuma capacidade nova e criada |

O wizard nao adiciona resultado de negocio: ele encurta o caminho ate resultados
ja certificados.

---

# 4. API

Uma unica superficie aditiva. As 107 operacoes certificadas permanecem
inalteradas; o inventario passa a 108.

- `POST /credit/carteiras/{carteira_id}/lancamentos` — lanca o emprestimo em uma
  transacao a partir do Devedor e das condicoes. `Idempotency-Key` obrigatoria.

O caminho evita colisao com `POST /credit/contratos/{contrato_id}/emprestimos`,
que ja existe e cria o Emprestimo a partir de um Contrato ja liberado.

Nenhuma operacao existente muda de forma, de codigo de erro ou de permissao. O
wizard nao consome nenhum endpoint que o backend nao publique.

---

# 5. Fases e IMPs

## Fase A — Backend

### IMP-305 - Servico de lancamento composto

- **Objetivo:** um servico de aplicacao que, sob um unico `UnitOfWork`, resolve
  ou cria o Devedor, percorre Proposta e Contrato pelos metodos de agregado,
  cria o Emprestimo e gera o plano de parcelas.
- **Componentes:** `src/emprestimo/application/lancamento.py` (novo),
  `tests/integration/application/`.
- **Dependencias:** nenhuma.
- **Criterios:** invariantes executadas, nao contornadas — cada transicao passa
  pelo metodo do agregado com `usuario_id`; falha em qualquer passo desfaz tudo;
  nenhum calculo financeiro fora do Motor.
- **Suite minima:** integracao com PostgreSQL real, incluindo rollback por passo.

### IMP-306 - Endpoint de lancamento

- **Objetivo:** expor a operacao com `Idempotency-Key` obrigatoria.
- **Componentes:** `presentation/api/lancamento_routes.py`,
  `lancamento_schemas.py`, `main.py`, `openapi.py`.
- **Dependencias:** IMP-305.
- **Criterios:** replay com a mesma chave devolve o resultado original; payload
  divergente com a mesma chave e conflito; RBAC exige as permissoes de Devedor,
  Comercial, Contratos e Motor; OpenAPI e snapshot atualizados.
- **Suite minima:** integracao de API, contrato e idempotencia.

### IMP-307 - Comprovante

- **Objetivo:** gerar no backend o texto do comprovante e enfileirar o envio
  fora da transacao.
- **Componentes:** `application/comprovante.py`, `domain/credit/operacao_diaria.py`
  (valor `whatsapp` em `CanalComunicacao`), migration aditiva.
- **Dependencias:** IMP-305.
- **Criterios:** texto usa somente valores retornados pelo Motor; envio nao
  bloqueia o commit; falha de canal nao desfaz o lancamento.
- **Suite minima:** unidade da montagem, integracao do enfileiramento.

## Fase B — Frontend

### IMP-308 - Wizard de lancamento

- **Objetivo:** tres passos — Devedor, Condicoes, Confirmacao — chamando o
  endpoint uma unica vez.
- **Componentes:** `frontend/src/app/app/lancamentos/`, componentes e BFF.
- **Dependencias:** IMP-306.
- **Criterios:** campos tipados, sem JSON cru; sem UUID digitado pelo operador;
  sem aritmetica no frontend; erro preserva o que foi digitado.
- **Suite minima:** unidade, componente, BFF, Playwright.

### IMP-309 - Tela de emprestimos

- **Objetivo:** em andamento, quitados e encerrados, a partir do estado oficial.
- **Dependencias:** nenhuma.
- **Criterios:** nenhuma classificacao calculada no frontend.

### IMP-310 - Devedor com situacao do emprestimo

- **Objetivo:** o detalhe do Devedor exibe os emprestimos dele.
- **Dependencias:** IMP-309.
- **Criterios:** somente leitura, somente valores retornados.

## Fase C — Certificacao

### IMP-311 - Jornada real e recertificacao

- **Objetivo:** cenario que preenche o wizard na interface contra FastAPI e
  PostgreSQL reais, ate o plano de parcelas.
- **Dependencias:** IMP-308..310.
- **Criterios:** o cenario falha se a cadeia quebrar em qualquer ponto; gates
  completos verdes; matriz atualizada.

---

# 6. Gates

- `uv run pytest -q`, `ruff`, `black --check`, `mypy src tests`;
- `npm run docs:validate` com 0 erros e sem avisos novos;
- `npm run docs:test`, `node scripts/tests/test-plan-025-contracts.js`;
- frontend: typecheck, lint, unit, component, contract, BFF, build;
- Playwright de jornada real contra stack real;
- `git diff --check`.

**Aviso transitorio esperado.** Enquanto o IMP-306 nao existir, `docs:validate`
reporta `endpoint "POST /credit/carteiras/{}/lancamentos" planejado e ainda nao
implementado`, elevando a baseline de 29 para 30 avisos. O aviso e verdadeiro e
descreve o estado real; suprimi-lo seria mascarar o planejamento. Volta a 29
quando o endpoint for publicado.

---

# 7. Riscos

| Risco | Tratamento |
|---|---|
| Transacao longa demais | medir o passo de geracao de parcelas |
| Wizard divergir do que o Motor aceita | jornada real, como no IMP-304 |
| Telas antigas divergirem do wizard | ambos chamam a mesma operacao |
| Comprovante travar o lancamento | envio fora da transacao |

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-16 | Plano do wizard de lancamento: operacao composta, endpoint, comprovante, wizard e telas de leitura. |
