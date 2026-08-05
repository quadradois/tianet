# FEATURE-003 — Product Discovery — Atualizar Tenant

**ID:** FEATURE-003

**Tipo:** Artefato de Discovery (engenharia de produto)

**Status:** Em revisão

---

# 1. Objetivo de Negócio

Disponibilizar ao Administrador da Plataforma a capacidade de atualizar os
dados cadastrais de um Tenant já provisionado, garantindo que as informações
institucionais da organização permaneçam corretas e atualizadas durante todo
o seu ciclo de vida (EPIC-001 §3 — "atualização cadastral").

A atualização cadastral é a primeira etapa da manutenção do Tenant: ela
preserva a qualidade dos dados institucionais que alimentam a consulta
(FEATURE-002) e prepara o terreno para a gestão do estado operacional
(FEATURE-004), sem misturar as responsabilidades de cada Feature.

# 2. Valor Entregue ao Usuário

- O Administrador da Plataforma corrige e mantém os dados institucionais da
  organização sem recriar o Tenant;
- A atualização reflete imediatamente nas consultas (FEATURE-002), mantendo
  consistência entre a informação cadastrada e a informação exibida;
- A operação é de escrita restrita e auditada (ADR-002), preservando a
  governança exigida por PRODUCT-001 §3;
- Sem esta Feature, qualquer erro cadastral exigiria recriar a organização,
  com perda do histórico, das Carteiras e dos Usuários — inviável no ciclo
  de vida operacional.

# 3. Escopo

- Atualizar o nome institucional do Tenant por ID (UUID);
- Validar os dados de entrada antes da persistência;
- Retornar os dados atualizados no mesmo contrato de consulta (TenantResponse
  — DA-004 da FEATURE-002);
- Registrar a atualização na trilha de auditoria (ADR-002).

# 4. Fora do Escopo

- Alteração do identificador institucional (imutável — ver §6);
- Transições de estado operacional (provisao → ativo → inativo) — pertencem
  exclusivamente à FEATURE-004;
- Gerenciamento de Usuários (EPIC-002), Carteiras (EPIC-003) e Configurações
  (EPIC-005);
- Autenticação e autorização (EPIC-006);
- Qualquer operação financeira ou regra do Credit Context.

# 5. Regras de Negócio

- RB-001: Atualizar um Tenant inexistente retorna erro de "não encontrado"
  (404), no mesmo padrão da consulta por ID (US-009);
- RB-002: A atualização é exclusivamente cadastral — não altera o estado
  operacional nem dispara efeitos colaterais sobre Carteiras, Usuários ou
  Configurações;
- RB-003: O nome da organização é obrigatório e não vazio, respeitando os
  limites do contrato de entrada vigente (≤ 200 caracteres, alinhado ao
  TenantCreateRequest da FEATURE-001);
- RB-004: O identificador institucional é imutável após a criação — dado
  estável de integração (US-010), sua alteração está fora do escopo do MVP;
- RB-005: A unicidade do Tenant não é afetada: o nome não é único; o
  identificador institucional permanece sob a constraint UNIQUE criada na
  FEATURE-001;
- RB-006: Toda atualização é registrada na trilha de auditoria (ADR-002) —
  eventos de início, sucesso e falha/rollback;
- RB-007: A atualização é idempotente por natureza (repetição do mesmo
  payload não produz efeito duplo) — não exige Idempotency-Key, diferentemente
  do provisionamento (FEATURE-001).

# 6. Dados que Podem Ser Alterados

- nome — atualizável (obrigatório, não vazio, ≤ 200 caracteres);
- identificador_institucional — imutável no MVP (dado estável usado por
  integrações externas via US-010; alteração exigiria fluxo de migração com
  dupla escrita e janela de inconsistência);
- id e criado_em — imutáveis (gerados na criação);
- estado — fora do escopo (FEATURE-004);
- Entidades filhas (Usuários, Carteiras, Configurações) — fora do escopo
  (EPIC-002, EPIC-003, EPIC-005).

# 7. Restrições de Atualização

- A atualização ocorre por ID (UUID) do Tenant — mesmo identificador da
  consulta por ID (US-009);
- Leitura e escrita ocorrem dentro de uma transação única via Unit of Work —
  sem atualização parcial em caso de falha;
- A resposta utiliza DTO específico da camada Presentation (TenantResponse,
  reutilizado da FEATURE-002 — DA-004), sem exposição de dados internos de
  infraestrutura (RA-012);
- A autorização permanece dependente de EPIC-006, utilizando o mecanismo
  provisório do MVP até lá (alinhado ao DA-005 da FEATURE-002).

# 8. Dependências

- FEATURE-001 — Criar Tenant (produz os dados atualizados; define o contrato
  de entrada e a constraint UNIQUE do identificador);
- FEATURE-002 — Consultar Tenant (fornece o DTO de resposta TenantResponse —
  DA-004 — e o padrão de 404);
- EPIC-001 — Gerenciar Tenant (guarda o escopo da Feature);
- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant (isolamento);
- DOMAIN-017 — Aggregate Tenant (identidade e invariantes);
- DECISION-001 / ADR-001 — stack e arquitetura (camadas Presentation →
  Application → Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação (escrita é auditada).

# 9. Casos de Uso

- UC-001 — Atualizar dados cadastrais do Tenant por ID: informar o ID e o
  novo nome da organização; obter na resposta os dados institucionais
  atualizados, no mesmo conjunto de campos da consulta (FEATURE-002);
- UC-002 — Confirmar atualização: a resposta reflete o estado cadastral
  vigente após a operação, permitindo a conferência imediata do resultado.

# 10. Riscos

- R-01 — Alteração do identificador institucional quebraria contratos de
  integração externa (US-010) e a estabilidade da chave: mitigado pela
  imutabilidade no MVP (RB-004);
- R-02 — Exposição de dados internos: mitigado por DTO único (TenantResponse,
  DA-004) e por testes de serialização que travam o conjunto de campos
  expostos (mesma mitigação da FEATURE-002, R-01);
- R-03 — Atualização sem trilha de auditoria viola ADR-002: mitigado por
  registro de eventos início/sucesso/falha no fluxo (RB-006);
- R-04 — Atualização parcial em falha de persistência: mitigado por transação
  única via Unit of Work;
- R-05 — Condição de corrida em atualização concorrente (leitura-escrita):
  mitigado pela transação única do UoW; versionamento otimista do agregado é
  recomendação futura (RA-001/RA-002 do AG-003), não bloqueante para o MVP;
- R-06 — Sobreposição com a FEATURE-004 (estado operacional): escopo restrito
  a dados cadastrais; transições de estado permanecem exclusivas da
  FEATURE-004 (RB-002);
- R-07 — Divergência de contrato com a consulta (GET): a resposta reutiliza o
  TenantResponse (DA-004), evitando dois contratos concorrentes.

---

# User Stories Candidatas

Identificação das histórias necessárias para a FEATURE-003 (a materializar
somente após aprovação do Discovery):

- US-012 — Atualizar dados cadastrais do Tenant por ID (UC-001): alterar o
  nome institucional de um Tenant conhecido, com validação de entrada, 404
  para inexistente e resposta com os dados atualizados;
- US-013 — Registrar auditoria da atualização cadastral (UC-002/RB-006):
  persistir a trilha de auditoria da operação de escrita (ADR-002) — pode ser
  absorvida como critério transversal, a critério da revisão arquitetural.

Critérios de aceitação transversais propostos:

- escrita auditada (ADR-002), com eventos de início, sucesso e falha;
- resposta com DTO único (TenantResponse — DA-004), sem dados internos;
- 404 para Tenant inexistente;
- 422 para payload inválido;
- atualização refletida imediatamente nas consultas da FEATURE-002.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 0.1.0 | 02/08/2026 | Primeira versão do Discovery da FEATURE-003 — Atualizar Tenant, para revisão arquitetural. |
