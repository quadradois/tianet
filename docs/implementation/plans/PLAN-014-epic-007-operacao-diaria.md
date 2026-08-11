# PLAN-014 - Plano Tecnico do EPIC-007/Operacao Diaria

**ID:** PLAN-014

**Versao:** 1.0.0

**Status:** Implementado em 2026-08-11

---

# 1. Contexto

Este plano executa o EPIC-007/Operacao Diaria apos o encerramento funcional do
EPIC-005 (Motor Financeiro) e do EPIC-006 (IAM). O escopo é estritamente
operacional: acompanhamento diario de recuperacao, compromissos, comunicacao manual
e relatorios basicos, sem regra financeira definitiva fora do Motor.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-007-operacao-diaria-discovery.md`;
- `docs/product/credit/epics/EPIC-007-operacao-diaria.md`;
- `docs/product/credit/capabilities/PRODUCT-005-administrar-cobrancas.md`;
- `docs/product/credit/capabilities/PRODUCT-006-administrar-agenda.md`;
- `docs/product/credit/capabilities/PRODUCT-007-administrar-comunicacao.md`;
- `docs/product/credit/capabilities/PRODUCT-008-administrar-relatorios.md`;
- `docs/product/credit/features/FEATURE-028-gerir-cobranca-manual.md`;
- `docs/product/credit/features/FEATURE-029-administrar-agenda-operacional.md`;
- `docs/product/credit/features/FEATURE-030-registrar-comunicacao-manual.md`;
- `docs/product/credit/features/FEATURE-031-consultar-relatorios-operacionais.md`;
- `docs/product/credit/user-stories/US-075-consultar-fila-de-cobranca.md`;
- `docs/product/credit/user-stories/US-076-registrar-acao-de-cobranca.md`;
- `docs/product/credit/user-stories/US-077-registrar-promessa-de-pagamento.md`;
- `docs/product/credit/user-stories/US-078-acompanhar-promessa-de-pagamento.md`;
- `docs/product/credit/user-stories/US-079-consultar-agenda-operacional.md`;
- `docs/product/credit/user-stories/US-080-criar-compromisso-e-lembrete.md`;
- `docs/product/credit/user-stories/US-081-manter-compromisso-de-agenda.md`;
- `docs/product/credit/user-stories/US-082-registrar-comunicacao-manual.md`;
- `docs/product/credit/user-stories/US-083-consultar-historico-de-comunicacao.md`;
- `docs/product/credit/user-stories/US-084-consultar-resumo-da-carteira.md`;
- `docs/product/credit/user-stories/US-085-consultar-vencimentos-e-inadimplencia.md`;
- `docs/product/credit/user-stories/US-086-consultar-pagamentos-e-operacoes-encerradas.md`;
- `docs/product/credit/user-stories/US-087-consultar-fluxo-previsto-e-realizado.md`;
- `docs/product/credit/user-stories/US-088-impedir-calculo-financeiro-fora-do-motor-na-operacao-diaria.md`;
- `docs/implementation/backlogs/PLAN-013-execution-backlog.md`;
- `docs/domain/credit/events/DOMAIN-011-event-emprestimo-criado.md`;
- `docs/domain/credit/events/DOMAIN-012-event-pagamento-registrado.md`;
- `docs/domain/credit/events/DOMAIN-013-event-emprestimo-quitado.md`;

---

# 3. Situacao Atual

## Concluido e pronto para reutilizar

- IAM operacional em produção lógica (authN, RBAC, respostas 401/403/404;
  OpenAPI protegida);
- Cadastros, Contratos e Motor Financeiro persistidos e testados;
- EPIC-007 Discovery/SDD com Product/Capability/Feature/US emitidos;
- Governança documental e testes de rastreabilidade da EPIC-007 já estabilizados;
- guardrails de não-cálculo financeiro no contexto operacional definidos.

## Pendencias para este plano

- implementação de serviços/rotas/regras do EPIC-007;
- persistência de filas, promessa, agenda, comunicacao e relatorios de leitura;
- recertificação técnica e revisão adversarial final do epic.

---

# 4. Decisoes Tecnicas

## D1 — Operacao Diaria e não Cálculo Definitivo

O EPIC-007 consome fatos oficiais do Motor (`SituacaoParcelaNaDataV1`,
`PagamentoEstornadoV1`, `EncerramentoOperacaoV1`) e não calcula juros, multa,
amortizacao, saldo ou quitacao.

## D2 — Cadeia Canonica Obrigatoria

Toda acao (cobranca, agenda, comunicacao) referencia
`Tenant/Carteira/Devedor` como trilha canônica mínima.

## D3 — Estado de Promessa Deterministico

As transições de promessa seguem a tabela DA-718, com invalidacao condicional após
estorno e sem automação de descoberta.

## D4 — Erros Protegidos e Idempotencia

Escritas aceitam idempotência com chave quando aplicável; payload divergente deve
retornar 409; malformado 400; cross-tenant 404 lógico.

## D5 — Projecao de Relatorios sem Mutação

Relatórios e agregacoes usam dados oficiais e apenas agregacoes permitidas
(`count`, `sum`, `group` com campos rastreáveis), sem mutação de estado.

---

# 5. Modelo de Dados Candidata

Migrations previstas para o bloco operacional:

- `cobranca_caso` (tenant, carteira, devedor, emprestimo, total_pendente,
  estado, origem, criado_em);
- `cobranca_acao` (caso, tipo, resultado, responsavel, data, observacao,
  payload);
- `promessa_pagamento` (caso, parcela, valor_pedido, data_vencimento,
  estado, id_promessa_legal, cadeia);
- `promessa_apropriacao` (promessa, pagamento_id, valor_aplicado,
  data_referencia, origem_fato, criado_em);
- `agenda_item` (tipo_item, tenant, carteira, devedor, emprestimo, caso, titulo,
  status, vencimento, prioridade, responsavel, canal);
- `lembrete` (agenda_item, dispara_em, mensagem, estado);
- `comunicacao_registro` (tenant, carteira, devedor, emprestimo, caso, canal,
  resultado, responsavel, data, observacao);
- `relatorio_operacional_cache` (tenant, carteira, janela_referencia,
  familia_relat, payload_json, gerado_em) — projeção somente leitura.

Restrições mínimas:

- FK para Tenant, Carteira e Devedor, e para Emprestimo/Parcela quando aplicável;
- unicidade por chave idempotente onde suportada;
- imutabilidade de histórico de estado (append-only) para ações e histórico;
- isolamento cross-tenant/carteira com escopo de consulta;
- downgrade seguro com dados de leitura recreáveis.

---

# 6. API

Rotas implementadas do EPIC-007:

- `GET /credit/cobrancas/casos` consulta fila diaria de cobranca;
- `POST /credit/cobrancas/casos/{cobranca_caso_id}/acoes` registra acao de
  cobranca;
- `POST /credit/cobrancas/casos/{cobranca_caso_id}/promessas` registra promessa
  de pagamento;
- `POST /credit/cobrancas/promessas/{promessa_id}/apropriacoes` apropria
  pagamento informado pelo Motor a uma promessa;
- `GET /credit/agenda` consulta agenda operacional por periodo e filtros;
- `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos`
  cria compromisso de agenda;
- `POST /credit/agenda/compromissos/{agenda_item_id}/lembretes` cria lembrete
  associado ao compromisso;
- `POST /credit/agenda/compromissos/{agenda_item_id}/reagendar` reagenda
  compromisso;
- `POST /credit/agenda/compromissos/{agenda_item_id}/concluir` conclui
  compromisso;
- `POST /credit/agenda/compromissos/{agenda_item_id}/cancelar` cancela
  compromisso;
- `POST /credit/agenda/lembretes/{lembrete_id}/reagendar` reagenda lembrete;
- `POST /credit/agenda/lembretes/{lembrete_id}/enviar` marca lembrete como
  enviado;
- `POST /credit/agenda/lembretes/{lembrete_id}/concluir` conclui lembrete;
- `POST /credit/agenda/lembretes/{lembrete_id}/cancelar` cancela lembrete;
- `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes`
  registra comunicacao manual;
- `GET /credit/comunicacoes` consulta historico de comunicacao;
- `GET /credit/carteiras/{carteira_id}/relatorios/resumo` consulta resumo
  operacional da carteira;
- `GET /credit/carteiras/{carteira_id}/relatorios/vencimentos` consulta
  vencimentos e inadimplencia;
- `GET /credit/carteiras/{carteira_id}/relatorios/pagamentos` consulta
  pagamentos e operacoes encerradas;
- `GET /credit/carteiras/{carteira_id}/relatorios/fluxo` consulta fluxo previsto
  e realizado.

- rotas de Cobranca/Promessa:
  - consulta de fila diaria;
  - registrar acao de cobrança;
  - registrar promessa;
  - reavaliar/acompanhar promessa (endpoint de leitura + reavalidação interna).
- rotas de Agenda:
  - consultar agenda por carteira/periodo;
  - criar item e lembrete;
  - reagendar, concluir e cancelar itens.
- rotas de Comunicação:
  - registrar comunicacao;
  - consultar histórico.
- rotas de Relatórios:
  - resumo da carteira;
  - vencimentos e inadimplência;
  - pagamentos e operacoes encerradas;
  - fluxo previsto vs realizado.

Todas as rotas devem existir sob `/credit`, com proteção via IAM (token + RBAC) e
erros documentados (`400/401/403/404/409` quando aplicável).

---

# 7. Estrategia de Testes

- **Unit domain cobranca**
- **Unit domain agenda**
- **Unit domain comunicacao**
- **Unit domain relatorios (projeções/guardrails)**
- **Guardrail anti-cálculo financeiro fora do Motor**
- **Integration migrations** (upgrade/downgrade/upgrade)
- **Integration repositories** (islação de escopo, idempotência, cascata)
- **Unit application** por feature (cobranca, agenda, comunicacao, relatorios)
- **Integration application** (UoW, auditoria, idempotência, cross-tenant)
- **Integration API** (contratos de erro + proteção 401/403/404/409 + paginação/filtros)
- **Recertificação EPIC-007** e revisão adversarial final.

---

# 8. Ordem de Implementacao

1. suites e guardrails antes de código;
2. domínio operacional (cobranca/agenda/comunicacao/relatorios);
3. persistência e integração de repositorios no UoW;
4. serviços de aplicação;
5. IAM/rotas/OpenAPI;
6. recertificação global do EPIC com revisão adversarial.

Cada tarefa inicia somente com dependências satisfeitas no backlog.

---

# 9. Gates de Aceite

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- 401 para sem token em recursos protegidos;
- 403 para principal sem permissão;
- 404 lógico para recurso não autorizado ou externo à carteira;
- 409 para cadeia incompatível, idempotência divergente ou transição invalida;
- `400` para payload/filtro/data malformado;
- ausência de cálculos financeiros em rotinas de operação;
- recertificação adversarial (sem achados funcionais/estruturais em aberto).

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-10 | Plano tecnico inicial do EPIC-007/Operacao Diaria apos revisao documental completa. |
