# FEATURE-004 — Product Discovery — Inativar Tenant

**ID:** FEATURE-004

**Tipo:** Artefato de Discovery (engenharia de produto)

**Status:** Em revisão

---

# 1. Objetivo de Negócio

Completar o ciclo de vida do Aggregate Tenant (EPIC-001 §3 — "ativação e
inativação" e "administração do estado operacional"), permitindo ao
Administrador da Plataforma inativar uma organização que não opera mais na
plataforma — e reativá-la quando necessário — sem destruir seus dados e
preservando a governança exigida por PRODUCT-001 §3.

A inativação é a última etapa da administração do estado operacional do
Tenant: ela sinaliza formalmente a suspensão da operação da organização,
fechando o ciclo nascimento (FEATURE-001) → consulta (FEATURE-002) →
atualização (FEATURE-003) → inativação (FEATURE-004).

# 2. Valor Entregue ao Usuário

- O Administrador da Plataforma suspende formalmente a operação de uma
  organização sem removê-la, preservando seu histórico, suas Carteiras, seus
  Usuários e suas Configurações;
- A inativação é visível e auditável: o estado operacional do Tenant reflete
  a situação real da organização nas consultas (FEATURE-002);
- A reativação permite restabelecer a organização sem recriar o
  provisionamento, preservando a continuidade operacional;
- Sem esta Feature, não há como sinalizar a suspensão de uma organização —
  comprometendo a governança do ciclo de vida exigida por PRODUCT-001 §3.

# 3. Escopo

- Inativar Tenant por ID (UUID): transição Ativo → Inativo;
- Reativar Tenant por ID (UUID): transição Inativo → Ativo;
- Registrar a transição na trilha de auditoria (ADR-002);
- Retornar o estado operacional atualizado no mesmo contrato de consulta
  (TenantResponse — DA-004 da FEATURE-002).

# 4. Fora do Escopo

- Alteração do identificador institucional (imutável — DA-006);
- Atualização de dados cadastrais (FEATURE-003);
- Exclusão física de Tenant ou de qualquer dado associado;
- Gerenciamento de Usuários (EPIC-002), Carteiras (EPIC-003) e Configurações
  (EPIC-005);
- Autenticação e autorização (EPIC-006);
- Qualquer operação financeira ou regra do Credit Context;
- Transição Provisão → Ativo na confirmação do provisionamento (FEATURE-001,
  UC-007 — já implementada, IMP-013).

# 5. Regras de Negócio

- RB-001: Inativar ou reativar um Tenant inexistente retorna erro de "não
  encontrado" (404), no mesmo padrão da consulta por ID (US-009);
- RB-002: A transição de estado é responsabilidade exclusiva do Domain —
  nenhuma regra de negócio é executada fora do Aggregate Tenant;
- RB-003: Apenas Tenants Ativos podem ser inativados (transição
  Ativo → Inativo); inativar um Tenant em Provisão ou já Inativo viola a
  máquina de estados do domínio (ViolacaoInvarianteError);
- RB-004: Apenas Tenants Inativos podem ser reativados (transição
  Inativo → Ativo); reativar um Tenant Ativo ou em Provisão viola a máquina
  de estados;
- RB-005: A inativação não altera dados cadastrais nem destrói entidades
  filhas (Usuários, Carteiras, Configurações) — é reversível via reativação;
- RB-006: Após a inativação, a consulta (FEATURE-002) e a atualização
  cadastral (FEATURE-003) permanecem permitidas — a inativação suspende a
  operação, não o acesso administrativo nem a leitura;
- RB-007: A transição é registrada na trilha de auditoria (ADR-002) — eventos
  de início, sucesso e falha/rollback;
- RB-008: A transição é idempotente por natureza (repetição da mesma
  requisição não produz efeito duplo quando o estado final já é o
  solicitado? Não — em estado divergente, viola a máquina de estados) —
  o contrato deverá definir o comportamento de estado divergente na
  materialização da Feature (aberto para a revisão arquitetural).

# 6. Estados Envolvidos

O Aggregate Tenant possui três estados operacionais (DOMAIN-017/PLAN-001 §5,
TenantState — provisao | ativo | inativo):

- Provisão — estado inicial, criado no provisionamento (FEATURE-001);
  transita para Ativo na confirmação do provisionamento (UC-007, IMP-013) —
  transição fora do escopo desta Feature;
- Ativo — estado operacional da organização; único estado que admite
  inativação (UC-001);
- Inativo — organização suspensa; dados preservados; admite reativação
  (UC-002) para o estado Ativo.

Transições definidas na máquina de estados do domínio:

- Provisão → Ativo (FEATURE-001 — já implementada);
- Ativo → Inativo (FEATURE-004 — UC-001);
- Inativo → Ativo (FEATURE-004 — UC-002).

Transições inexistentes (bloqueadas pelo Domain):

- Ativo → Ativo / Inativo → Inativo (estado já solicitado);
- Provisão → Inativo (inativação não se aplica a Tenant em provisionamento);
- Qualquer transação a partir de Tenant inexistente (404).

# 7. Restrições para Inativação

- A inativação (e a reativação) ocorre por ID (UUID) do Tenant — mesmo
  identificador da consulta por ID (US-009);
- Apenas Tenants Ativos podem ser inativados; apenas Tenants Inativos podem
  ser reativados (RB-003/RB-004) — nenhuma exceção no MVP;
- A transição não exige dados adicionais além da identificação do Tenant
  (sem payload de negócio na inativação/reativação);
- Leitura e escrita ocorrem dentro de uma transação única via Unit of Work —
  sem transição parcial em caso de falha;
- A resposta utiliza DTO específico da camada Presentation (TenantResponse,
  reutilizado da FEATURE-002 — DA-004), sem exposição de dados internos de
  infraestrutura (RA-012);
- A autorização permanece dependente de EPIC-006, utilizando o mecanismo
  provisório do MVP até lá (alinhado ao DA-005 da FEATURE-002).

# 8. Dependências

- FEATURE-001 — Criar Tenant (define os estados iniciais e a transição
  Provisão → Ativo na confirmação do provisionamento);
- FEATURE-002 — Consultar Tenant (fornece o DTO de resposta TenantResponse —
  DA-004 — e o padrão de 404);
- FEATURE-003 — Atualizar Tenant (convive com a inativação — RB-006);
- EPIC-001 — Gerenciar Tenant (guarda o escopo da Feature);
- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant (isolamento);
- DOMAIN-017 — Aggregate Tenant (estado operacional e invariantes);
- DECISION-001 / ADR-001 — stack e arquitetura (camadas Presentation →
  Application → Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação (escrita é auditada).

# 9. Casos de Uso

- UC-001 — Inativar Tenant por ID: informar o ID de um Tenant Ativo; obter
  na resposta o estado operacional atualizado (inativo), no mesmo conjunto
  de campos da consulta (FEATURE-002);
- UC-002 — Reativar Tenant por ID: informar o ID de um Tenant Inativo; obter
  na resposta o estado operacional atualizado (ativo).

# 10. Riscos

- R-01 — Inativação indevida de Tenant ainda operacional: mitigado pela
  transição exclusiva no Domain (RB-003) e pela trilha de auditoria (ADR-002);
- R-02 — Perda de acesso aos dados após a inativação: mitigado por RB-005 e
  RB-006 (dados preservados; consulta e atualização permanecem permitidas);
- R-03 — Confusão com a transição do provisionamento (Provisão → Ativo,
  FEATURE-001): mitigado pela máquina de estados explícita (RB-003/RB-004);
- R-04 — Exposição de dados internos: mitigado por DTO único (TenantResponse,
  DA-004) e por testes de serialização (mesma mitigação da FEATURE-002);
- R-05 — Condição de corrida em transição concorrente: mitigado por transação
  única via Unit of Work; versionamento otimista é recomendação futura
  (DA-008, não bloqueante para o MVP);
- R-06 — Sobreposição com FEATURE-003 (dados cadastrais): escopo restrito ao
  estado operacional; dados cadastrais permanecem exclusivos da FEATURE-003
  (RB-002, RB-006);
- R-07 — Contrato de estado divergente ambíguo (RB-008): decidido na
  materialização da Feature, alinhado ao padrão de erro da API (400/409/422).

---

# User Stories Candidatas

Identificação das histórias necessárias para a FEATURE-004 (a materializar
somente após aprovação do Discovery):

- US-013 — Inativar Tenant (UC-001): suspender a operação de um Tenant Ativo,
  com validação da máquina de estados, 404 para inexistente e resposta com o
  estado atualizado;
- US-014 — Reativar Tenant (UC-002): restabelecer a operação de um Tenant
  Inativo, com validação da máquina de estados, 404 para inexistente e
  resposta com o estado atualizado.

Critérios de aceitação transversais propostos:

- transição de estado exclusiva no Domain (RB-002);
- escrita auditada (ADR-002), com eventos de início, sucesso e falha;
- resposta com DTO único (TenantResponse — DA-004), sem dados internos;
- 404 para Tenant inexistente;
- 422 para payload inválido;
- estado atualizado refletido imediatamente nas consultas da FEATURE-002.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 0.1.0 | 02/08/2026 | Primeira versão do Discovery da FEATURE-004 — Inativar Tenant, para revisão arquitetural. |
