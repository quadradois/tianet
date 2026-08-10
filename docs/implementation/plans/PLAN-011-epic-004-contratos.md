# PLAN-011 - Plano Tecnico do EPIC-004/Contratos

**ID:** PLAN-011

**Versao:** 1.0.0

**Status:** Implementado em 2026-08-09

---

# 1. Objetivo

Implementar o EPIC-004/Contratos de Credito no Credit Context, seguindo o pacote
Product/SDD materializado para formalizar contratos a partir de propostas
aprovadas.

O escopo cobre dominio de Contratos, persistencia, application services, API,
RBAC, auditoria, OpenAPI e suites de guardrail que impedem calculo financeiro
definitivo fora do Motor Financeiro.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-004-contratos-discovery.md`;
- `docs/product/credit/capabilities/PRODUCT-004-administrar-operacoes-de-credito.md`;
- `docs/product/credit/epics/EPIC-004-contratos-de-credito.md`;
- `docs/product/credit/features/FEATURE-018-formalizar-contrato-de-credito.md`;
- `docs/product/credit/features/FEATURE-019-consultar-contratos.md`;
- `docs/product/credit/features/FEATURE-020-registrar-assinatura-contratual.md`;
- `docs/product/credit/features/FEATURE-021-liberar-contrato-para-motor-financeiro.md`;
- `docs/product/credit/features/FEATURE-022-cancelar-encerrar-contrato.md`;
- `docs/product/credit/user-stories/US-053-criar-contrato-a-partir-proposta-aprovada.md`;
- `docs/product/credit/user-stories/US-054-validar-proposta-aprovada-para-contrato.md`;
- `docs/product/credit/user-stories/US-055-consultar-contrato-por-id.md`;
- `docs/product/credit/user-stories/US-056-listar-contratos.md`;
- `docs/product/credit/user-stories/US-057-registrar-assinatura-contratual.md`;
- `docs/product/credit/user-stories/US-058-consultar-historico-contratual.md`;
- `docs/product/credit/user-stories/US-059-liberar-contrato-para-motor-financeiro.md`;
- `docs/product/credit/user-stories/US-060-impedir-liberacao-sem-assinatura.md`;
- `docs/product/credit/user-stories/US-061-cancelar-contrato-nao-liberado.md`;
- `docs/product/credit/user-stories/US-062-encerrar-contrato-sem-alterar-operacao.md`;
- `docs/domain/credit/entities/DOMAIN-003-entity-contrato-de-credito.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md`.

---

# 3. Situacao Atual

## Ja implementado - reutilizar

- IAM operacional com Principal autenticado, RBAC e contratos HTTP 401/403/404;
- Cadastro de Devedores com validacao de Devedor ativo e isolamento por Carteira;
- Comercial com `PropostaAprovadaLogica` como saida de proposta aprovada;
- auditoria append-only e Unit of Work reutilizaveis;
- pipeline de qualidade e validacao reproduzivel de migrations;
- padroes REST de API, schemas Pydantic, dependencies e OpenAPI.

## Ainda nao implementado

- dominio Contratos: `ContratoCredito`, estados, eventos e invariantes;
- guardrail anti-Motor para o contexto Contratos;
- ports e repositories de Contratos;
- migration aditiva de contratos;
- application services para formalizacao, consulta, assinatura, liberacao e
  cancelamento/encerramento;
- permissoes RBAC de Contratos;
- endpoints HTTP protegidos por IAM/RBAC;
- suites unitarias, integracao, API, OpenAPI e recertificacao.

---

# 4. Decisoes Tecnicas

## DA-501 - Contrato nasce de proposta aprovada

Contrato de Credito so pode ser criado a partir da saida logica de proposta
aprovada do EPIC-003. Proposta nao aprovada, inexistente, de outro Tenant ou com
Devedor inativo nao cria contrato.

## DA-502 - Contrato preserva snapshot contratual

Os parametros aprovados sao copiados defensivamente para o contrato. Apos
formalizacao, assinatura ou liberacao para Motor, parametros essenciais nao sao
alterados.

## DA-503 - Contratos nao executa Motor Financeiro

Contratos nao cria Emprestimo, Parcela ou Pagamento e nao calcula juros, saldo,
amortizacao, atraso, quitacao ou memoria de calculo. Sua saida para o EPIC-005 e
apenas um contrato formalizado/liberavel.

## DA-504 - Liberacao para Motor e logica

Liberar contrato significa disponibilizar uma entrada imutavel para o Motor
Financeiro futuro. Nao ha desembolso, integracao bancaria ou criacao de operacao
financeira no EPIC-004.

## DA-505 - RBAC por permissoes contratuais

Permissoes candidatas:

- `contratos.contrato.criar`;
- `contratos.contrato.ler`;
- `contratos.contrato.assinar`;
- `contratos.contrato.liberar`;
- `contratos.contrato.encerrar`.

## DA-506 - API aninhada sob Carteira quando cria/lista

Criacao e listagem usam `/credit/carteiras/{carteira_id}/contratos`. Consultas
por ID usam identificador global com isolamento por Tenant autenticado e 404
indistinguivel para cross-tenant.

---

# 5. Modelo de Dados

Migration aditiva prevista:

- `contrato_credito`: id, tenant_id, carteira_id, devedor_id,
  proposta_comercial_id, estado, parametros JSON, criado_por_usuario_id,
  formalizado_por_usuario_id opcional, formalizado_em opcional,
  assinado_por_usuario_id opcional, assinado_em opcional,
  liberado_por_usuario_id opcional, liberado_em opcional, motivo_encerramento
  opcional, criado_em, atualizado_em;
- `evento_contrato`: id, contrato_id, usuario_id, tipo, estado_anterior,
  estado_posterior, motivo opcional, criado_em.

Constraints minimas:

- FKs para `tenant`, `carteira`, `devedor`, `proposta_comercial` e `usuario`
  quando aplicavel;
- unicidade de `proposta_comercial_id` para impedir dois contratos da mesma
  proposta no MVP;
- indices por `tenant_id`, `carteira_id`, `devedor_id`, `estado` e `criado_em`;
- downgrade reversivel;
- nenhuma alteracao destrutiva em tabelas existentes.

---

# 6. API

Rotas candidatas do EPIC-004:

- `POST /credit/carteiras/{carteira_id}/contratos` cria contrato a partir de
  proposta aprovada;
- `GET /credit/carteiras/{carteira_id}/contratos` lista contratos;
- `GET /credit/contratos/{contrato_id}` consulta contrato por ID;
- `GET /credit/contratos/{contrato_id}/historico` consulta historico contratual;
- `POST /credit/contratos/{contrato_id}/assinar` registra assinatura ou
  formalizacao;
- `POST /credit/contratos/{contrato_id}/liberar-para-motor` retorna saida
  logica para Motor futuro;
- `POST /credit/contratos/{contrato_id}/cancelar` cancela contrato nao liberado;
- `POST /credit/contratos/{contrato_id}/encerrar` encerra contrato sem alterar
  operacao financeira.

Contratos de erro:

- 401 para token ausente, invalido ou expirado;
- 403 para Principal autenticado sem permissao contratual;
- 404 para Carteira/Contrato/Proposta inexistente ou de outro Tenant;
- 409 para transicao de estado invalida ou contrato duplicado por proposta;
- 400 para entrada invalida, seguindo o handler global de `RequestValidationError`.

---

# 7. Estrategia de Testes

- **Unit domain Contratos:** estados, invariantes, snapshot imutavel, transicoes
  validas e invalidas;
- **Guardrail Motor:** testes que falham se Contratos criar Emprestimo, Parcela,
  Pagamento ou executar calculo financeiro definitivo;
- **Integration migrations:** ciclo upgrade/downgrade/upgrade e indices/FKs;
- **Integration repositories:** round-trip real de contrato e eventos por Tenant;
- **Unit application:** formalizacao, consulta, assinatura, liberacao,
  cancelamento/encerramento e auditoria com fakes;
- **Integration application:** UoW, auditoria, rollback e validacao de proposta
  aprovada;
- **Integration API:** contratos HTTP 200/201/400/401/403/404/409 e RBAC;
- **OpenAPI:** security Bearer e respostas documentadas;
- **Regression Comercial/IAM/Cadastro:** proposta aprovada, Devedor ativo,
  cross-tenant e permissoes ausentes.

---

# 8. Ordem de Implementacao

1. suites de dominio e guardrail antes do codigo;
2. dominio Contratos;
3. migrations e repositories;
4. application services;
5. catalogo RBAC e auditoria;
6. API e OpenAPI;
7. recertificacao e revisao adversarial.

Cada tarefa inicia somente com suas dependencias concluidas e sua suite minima
definida.

---

# 9. Estrategia de Rollout

- migration aditiva, sem backfill obrigatorio;
- endpoints novos protegidos desde o nascimento;
- nenhum endpoint existente muda de contrato;
- rollback por downgrade das tabelas contratuais enquanto EPIC-005 nao consumir
  contratos;
- release do EPIC-004 somente apos suite completa e gates globais verdes.

---

# 10. Riscos

| Risco | Mitigacao |
|---|---|
| Contratos absorver Motor Financeiro | Guardrail anti-Motor e DA-503. |
| Duplicar contrato para mesma proposta | Constraint unica por proposta no MVP. |
| Alterar snapshot apos formalizacao | Invariante de imutabilidade e testes de estado. |
| Liberacao parecer desembolso | DA-504 e nomes de API como liberacao logica. |
| Vazamento cross-tenant | Dependencias IAM/Carteira e 404 indistinguivel. |
| API sem RBAC | Permissoes contratuais desde a primeira exposicao. |

---

# 11. Gates de Aceite

O EPIC-004 so pode ser considerado pronto quando:

- `uv run pytest -q` passar;
- `uv run ruff check .` passar;
- `uv run black --check .` passar;
- `uv run mypy src tests` passar;
- `npm run docs:validate` passar com 0 erros;
- `npm run docs:test` passar;
- endpoints contratuais sem token responderem 401;
- token valido sem permissao contratual responder 403;
- recurso de outro Tenant responder 404;
- transicao invalida responder 409;
- entrada invalida responder 400;
- contrato liberado nao permitir alteracao de parametros essenciais;
- nenhuma suite, domain service ou application service de Contratos executar
  calculo financeiro definitivo.

---

# 12. Fora de Escopo

- Emprestimos, Parcelas e Pagamentos;
- Motor Financeiro;
- memoria de calculo, juros, amortizacao, saldo e quitacao;
- desembolso financeiro, banco, PIX ou boleto;
- assinatura digital externa;
- Event Bus externo ou mensageria;
- renegociacao financeira.

---

# 13. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Plano tecnico inicial do EPIC-004/Contratos com Product/SDD, backlog e guardrails anti-Motor. |
