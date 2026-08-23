# PLAN-013 - Plano Tecnico do EPIC-005/Motor Financeiro

**ID:** PLAN-013

**Versao:** 1.1.0

**Status:** Proposto

---

# 1. Objetivo

Implementar o EPIC-005/Emprestimos, Pagamentos e Motor Financeiro como Core
Domain operacional do Credit Context.

O plano cobre dominio, persistencia, application services, API, RBAC, OpenAPI,
auditoria, precisao financeira e guardrails que impedem calculo financeiro
definitivo fora do Motor.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-005-motor-financeiro-discovery.md`;
- `docs/product/credit/capabilities/PRODUCT-004-administrar-operacoes-de-credito.md`;
- `docs/product/credit/epics/EPIC-005-emprestimos-pagamentos-motor-financeiro.md`;
- `docs/product/credit/features/FEATURE-023-criar-emprestimo-a-partir-contrato-liberado.md`;
- `docs/product/credit/features/FEATURE-024-gerar-plano-de-parcelas.md`;
- `docs/product/credit/features/FEATURE-025-registrar-pagamento.md`;
- `docs/product/credit/features/FEATURE-026-consultar-saldo-e-memoria-de-calculo.md`;
- `docs/product/credit/features/FEATURE-027-quitar-e-renegociar-operacao.md`;
- `docs/product/credit/user-stories/US-063-criar-emprestimo-a-partir-contrato-liberado.md`;
- `docs/product/credit/user-stories/US-064-impedir-emprestimo-sem-contrato-liberado.md`;
- `docs/product/credit/user-stories/US-065-gerar-parcelas-do-emprestimo.md`;
- `docs/product/credit/user-stories/US-066-validar-periodos-financeiros-reais.md`;
- `docs/product/credit/user-stories/US-067-registrar-pagamento.md`;
- `docs/product/credit/user-stories/US-068-priorizar-juros-antes-da-amortizacao.md`;
- `docs/product/credit/user-stories/US-069-consultar-saldo-devedor.md`;
- `docs/product/credit/user-stories/US-070-consultar-memoria-de-calculo.md`;
- `docs/product/credit/user-stories/US-071-calcular-valor-para-quitacao.md`;
- `docs/product/credit/user-stories/US-072-quitar-emprestimo.md`;
- `docs/product/credit/user-stories/US-073-renegociar-operacao.md`;
- `docs/product/credit/user-stories/US-074-impedir-calculo-financeiro-fora-do-motor.md`;
- `docs/domain/credit/entities/DOMAIN-004-entity-emprestimo.md`;
- `docs/domain/credit/entities/DOMAIN-005-entity-parcela.md`;
- `docs/domain/credit/entities/DOMAIN-006-entity-pagamento.md`;
- `docs/domain/credit/services/DOMAIN-010-service-motor-financeiro.md`;
- `docs/foundation/FOUNDATION-004-core-domain.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`.

---

# 3. Situacao Atual

## Ja implementado - reutilizar

- IAM operacional com Principal autenticado, RBAC e contratos HTTP 401/403/404;
- Cadastro de Devedores e Carteiras com isolamento por Tenant;
- Comercial com proposta aprovada;
- Contratos com `ContratoLiberadoLogico` como saida para Motor;
- auditoria append-only;
- Unit of Work, migrations e repositories de contextos anteriores;
- pipeline de qualidade e validacao documental.

## Ainda nao implementado

- dominio operacional de Emprestimo, Parcela, Pagamento e Memoria de Calculo;
- regras de periodo financeiro, juros, amortizacao, saldo e quitacao;
- guardrails de precisao financeira e exclusividade do Motor;
- migrations de Emprestimos, Parcelas, Pagamentos e memorias;
- repositories e Unit of Work do Motor;
- application services de criacao, parcelas, pagamento, saldo, quitacao e
  renegociacao;
- permissoes RBAC financeiras;
- API e OpenAPI do Motor Financeiro;
- recertificacao completa do Core Domain.

---

# 4. Decisoes Tecnicas

## DA-701 - ContratoLiberadoLogico e a unica entrada de criacao

Emprestimo so nasce a partir de `ContratoLiberadoLogico`. O Motor nao aceita
payload avulso com parametros financeiros para criar operacao.

## DA-702 - Motor e a unica fonte oficial

Juros, amortizacao, saldo devedor, valor para quitacao e memoria de calculo sao
produzidos exclusivamente pelo Motor Financeiro.

## DA-703 - Precisao monetaria usa Decimal

Regras financeiras usam `Decimal` e politica explicita de arredondamento. `float`
e proibido no dominio financeiro e em services de calculo.

## DA-704 - Periodos financeiros sao explicitos

Todo calculo possui data inicial, data final e criterio de contagem de periodo.
Mes fixo implicito e proibido.

## DA-705 - Pagamento e fato financeiro idempotente

Pagamento recebido deve ter identificador idempotente quando possivel. O mesmo
Pagamento nao altera saldo duas vezes.

## DA-706 - Memoria de calculo acompanha toda saida financeira

Toda saida financeira relevante deve possuir memoria com entradas, parametros,
periodos, arredondamentos, passos e resultado.

## DA-707 - API do Motor nao recebe regra financeira arbitraria

Endpoints podem receber comandos de operacao, pagamento, consulta e data de
referencia. A regra financeira vem do contrato liberado ou de Configuracoes
financeiras futuras, nao do request livre.

## DA-708 - Renegociacao inicia rastreavel, nao sofisticada

O MVP deve registrar renegociacao como trilha financeira rastreavel. Politicas
avancadas podem ficar para ciclo posterior se exigirem decisao de produto.

---

# 5. Modelo de Dados

Migration aditiva prevista:

- `emprestimo`: id, tenant_id, carteira_id, devedor_id, contrato_id, estado,
  principal_original, moeda, parametros_financeiros JSON, criado_em,
  atualizado_em, quitado_em opcional;
- `parcela`: id, emprestimo_id, numero, vencimento, valor_previsto, principal,
  juros, encargos, estado, criada_em, atualizada_em;
- `pagamento`: id, emprestimo_id, chave_idempotencia opcional, valor_recebido,
  moeda, recebido_em, processado_em, distribuicao JSON, criado_por_usuario_id;
- `memoria_calculo`: id, emprestimo_id, pagamento_id opcional, tipo,
  data_referencia, entradas JSON, passos JSON, resultado JSON, criado_em;
- `evento_financeiro`: id, emprestimo_id, usuario_id opcional, tipo,
  payload JSON, criado_em.

Constraints minimas:

- FKs para Tenant, Carteira, Devedor, Contrato e Usuario quando aplicavel;
- unicidade de `contrato_id` em Emprestimo no MVP;
- unicidade de chave idempotente de Pagamento por Emprestimo quando informada;
- indices por `tenant_id`, `carteira_id`, `devedor_id`, `estado`,
  `vencimento`, `recebido_em` e `criado_em`;
- downgrade reversivel;
- nenhuma alteracao destrutiva em tabelas existentes.

---

# 6. API

Rotas candidatas do EPIC-005:

- `POST /credit/contratos/{contrato_id}/emprestimos` cria Emprestimo a partir de
  contrato liberado;
- `GET /credit/emprestimos/{emprestimo_id}` consulta Emprestimo por ID;
- `GET /credit/carteiras/{carteira_id}/emprestimos` lista Emprestimos;
- `POST /credit/emprestimos/{emprestimo_id}/parcelas` gera plano de Parcelas;
- `GET /credit/emprestimos/{emprestimo_id}/parcelas` lista Parcelas;
- `POST /credit/emprestimos/{emprestimo_id}/pagamentos` registra Pagamento;
- `POST /credit/pagamentos/{pagamento_id}/estornos` registra, com
  `Idempotency-Key` obrigatoria, o estorno parcial da sobra destinada a
  devolucao sem apagar o valor bruto recebido;
- `GET /credit/emprestimos/{emprestimo_id}/saldo` consulta saldo em data de
  referencia;
- `GET /credit/emprestimos/{emprestimo_id}/memoria-calculo` consulta memoria;
- `GET /credit/emprestimos/{emprestimo_id}/quitacao` consulta valor para
  quitacao em data de referencia;
- `POST /credit/emprestimos/{emprestimo_id}/quitacao` quita Emprestimo;
- `POST /credit/emprestimos/{emprestimo_id}/renegociacoes` registra
  renegociacao.

Contratos de erro:

- 401 para token ausente, invalido ou expirado;
- 403 para Principal autenticado sem permissao financeira;
- 404 para Contrato/Carteira/Emprestimo inexistente ou de outro Tenant;
- 409 para estado invalido, Emprestimo duplicado, Pagamento duplicado ou
  Emprestimo quitado recebendo Pagamento;
- 400 para entrada invalida, seguindo handler global.

---

# 7. Estrategia de Testes

- **Unit domain Motor:** Emprestimo, Parcela, Pagamento, periodos, estados,
  quitacao e invariantes;
- **Guardrail precisao:** proibicao de `float`, arredondamento explicito e uso
  de `Decimal`;
- **Guardrail exclusividade:** Comercial, Contratos e downstreams nao calculam
  juros, saldo, amortizacao ou quitacao;
- **Integration migrations:** upgrade/downgrade/upgrade, FKs, indices e
  constraints;
- **Integration repositories:** round-trip de Emprestimos, Parcelas, Pagamentos,
  memorias e eventos;
- **Unit application:** criacao, parcelas, pagamentos, saldo, quitacao e
  renegociacao com fakes;
- **Integration application:** UoW, auditoria, rollback e idempotencia;
- **Integration API:** 200/201/400/401/403/404/409 e isolamento cross-tenant;
- **OpenAPI:** Bearer security e respostas de erro documentadas;
- **Regression EPIC-004:** contrato liberado continua sendo entrada logica.

---

# 8. Ordem de Implementacao

1. suites de dominio, precisao e guardrail antes do codigo;
2. dominio de Emprestimo, Parcela, Pagamento, periodos, memoria e quitacao;
3. migrations, ORM, repositories e Unit of Work;
4. application services;
5. RBAC, schemas, API e OpenAPI;
6. recertificacao global e revisao adversarial.

Cada tarefa inicia somente com suas dependencias concluidas e sua suite minima
definida.

---

# 9. Estrategia de Rollout

- migration aditiva;
- endpoints novos protegidos desde o nascimento;
- nenhum endpoint de Contratos muda de contrato;
- criacao de Emprestimo idempotente por contrato liberado;
- rollback permitido enquanto nenhum downstream consumir eventos financeiros;
- release somente apos suites Python, qualidade e docs verdes.

---

# 10. Riscos

| Risco | Mitigacao |
|---|---|
| Erro de precisao monetaria | `Decimal`, politica de arredondamento e guardrail anti-float. |
| Calculo duplicado fora do Motor | guardrail de exclusividade por busca AST e testes. |
| Duplicar Emprestimo por Contrato | constraint unica e service idempotente. |
| Pagamento duplicado | chave idempotente e constraint por Emprestimo. |
| Saldo sem explicacao | memoria obrigatoria para saidas financeiras. |
| Periodo financeiro incorreto | VO de periodo com datas reais e suites de calendario. |
| Configuracoes financeiras ausentes | snapshot contratual no MVP e decisao futura documentada. |
| Renegociacao crescer demais | MVP limitado a trilha rastreavel e estados claros. |

---

# 11. Gates de Aceite

O EPIC-005 so pode ser considerado pronto quando:

- `uv run pytest -q` passar;
- `uv run ruff check .` passar;
- `uv run black --check .` passar;
- `uv run mypy src tests` passar;
- `npm run docs:validate` passar com 0 erros;
- `npm run docs:test` passar;
- endpoints financeiros sem token responderem 401;
- Principal sem permissao financeira responder 403;
- recurso cross-tenant responder 404;
- transicao financeira invalida responder 409;
- entrada invalida responder 400;
- OpenAPI declarar 400/401/403/404/409 nas rotas protegidas;
- guardrails comprovarem `Decimal`, ausencia de `float` e exclusividade do
  Motor.

---

# 12. Fora de Escopo

- Comercial;
- Contratos;
- Cobranca, Agenda, Comunicacao e Relatorios;
- integracao bancaria, PIX, boleto ou conciliacao;
- regras fiscais/regulatorias sem fonte normativa;
- motor de precificacao externa;
- configuracoes financeiras completas.

---

# 13. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-22 | IMP-332 declara o estorno parcial idempotente da sobra de Pagamento. |
| 1.0.0 | 2026-08-09 | Plano tecnico inicial do EPIC-005/Motor Financeiro com backlog, suites e guardrails de precisao. |
