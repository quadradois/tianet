# FEATURE-002 — Product Discovery — Consultar Tenant

**ID:** FEATURE-002

**Tipo:** Artefato de Discovery (engenharia de produto)

**Status:** Em revisão

---

# 1. Objetivo de Negócio

Disponibilizar ao Administrador da Plataforma a capacidade de consultar as
informações institucionais dos Tenants da TiaNet, incluindo o estado
operacional de cada organização, garantindo visibilidade e governança sobre
o ciclo de vida das organizações provisionadas (EPIC-001 §3 — "consulta de
Tenant" e "consulta das informações institucionais").

A consulta serve de suporte à confirmação do provisionamento (UC-007 da
FEATURE-001) e à operação administrativa diária da plataforma.

# 2. Valor Entregue ao Usuário

- O Administrador da Plataforma obtém, sob demanda, a situação atual de uma
  organização (identidade, estado operacional e data de criação);
- A consulta por lista permite visualizar o conjunto de organizações
  provisionadas, com paginação e filtro por estado;
- A consulta por identificador institucional permite integrar sistemas
  externos e confirmar a existência de uma organização por um dado humano e
  estável (não dependente de ID interno);
- Sem esta Feature, não há como verificar o que foi provisionado nem
  acompanhar a evolução do estado dos Tenants — comprometendo a governança
  exigida por PRODUCT-001 §3.

# 3. Escopo

- Consultar Tenant por ID (UUID);
- Consultar Tenant por identificador institucional;
- Listar Tenants com paginação, ordenação e filtro por estado operacional;
- Retornar apenas dados institucionais e de estado operacional;
- Suporte ao fluxo de confirmação da criação (FEATURE-001, UC-007).

# 4. Fora do Escopo

- Atualização de dados cadastrais (FEATURE-003);
- Ativação/inativação de Tenant (FEATURE-004);
- Exposição de Usuários, Carteiras ou Configurações do Tenant (EPIC-002,
  EPIC-003, EPIC-005);
- Autenticação e autorização (EPIC-006);
- Auditoria de consulta (apenas escrita é auditada — ADR-002);
- Qualquer operação de escrita no Tenant.

# 5. Regras de Negócio

- RB-001: Consultar um Tenant inexistente retorna erro de "não encontrado";
- RB-002: A consulta é exclusivamente de leitura — não altera o estado nem
  dispara efeitos colaterais;
- RB-003: Apenas dados institucionais e de estado são expostos; nenhum dado
  interno de infraestrutura (ex.: Idempotency-Key, trilhas de auditoria,
  metadados de persistência) é retornado (RA-012);
- RB-004: O isolamento entre Tenants é preservado (FOUNDATION-006 Princípio
  02/03): a consulta por ID/identificador não expõe dados de outras
  organizações;
- RB-005: A listagem é paginada e ordenada de forma determinística; o filtro
  por estado aceita apenas os estados operacionais oficiais
  (DOMAIN-017/PLAN-001 §5: Provisão, Ativo, Inativo);
- RB-006: A consulta por identificador institucional respeita a unicidade
  (constraint UNIQUE — FEATURE-001), resultando em no máximo um Tenant.

# 6. Dados Retornados

Por Tenant consultado/retornado:

- id (UUID);
- identificador_institucional;
- nome;
- estado operacional (provisao | ativo | inativo);
- criado_em (timestamp de criação).

Não são retornados: Usuários, Carteiras, Configurações, Idempotency-Key,
trilhas de auditoria ou qualquer campo interno de infraestrutura.

# 7. Restrições de Acesso

- A consulta destina-se ao Administrador da Plataforma (PRODUCT-001);
- Autenticação/autorização pertencem a EPIC-006 (fora do escopo do MVP) —
  até lá, o endpoint opera no contexto autenticado existente do MVP
  (PLAN-001 §6, FOUNDATION-008);
- Quando a autorização por perfil for implementada (EPIC-003), a consulta
  deve ser restrita aos perfis com permissão de leitura de Tenant, e o
  isolamento por Tenant (RB-004) deve ser aplicado por contexto do
  usuário autenticado.

# 8. Dependências

- FEATURE-001 — Criar Tenant (produz os dados consultados; GET por ID já
  parcialmente exposto via IMP-018);
- EPIC-001 — Gerenciar Tenant (guarda o escopo da Feature);
- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant (isolamento);
- DOMAIN-017 — Aggregate Tenant (estado operacional e invariantes);
- DECISION-001 / ADR-001 — stack e arquitetura (camadas Presentation →
  Application → Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação (define que consultas de
  leitura não geram trilha de auditoria nesta Feature).

# 9. Casos de Uso

- UC-001 — Consultar Tenant por ID: informar o ID e obter os dados
  institucionais, o estado atual e a data de criação;
- UC-002 — Consultar Tenant por identificador institucional: informar o
  identificador (dado estável da organização) e obter o mesmo conjunto de
  dados;
- UC-003 — Listar Tenants: obter a relação paginada de organizações com
  ordenação determinística e filtro opcional por estado operacional.

# 10. Riscos

- R-01 — Vazamento de dados internos: mitigado por DTOs específicos
  (RA-012) e por testes de serialização que travam o conjunto de campos
  expostos;
- R-02 — Listagem sem paginação degrada performance e consistência:
  mitigado por paginação obrigatória com ordenação determinística;
- R-03 — Ausência de autenticação no MVP expõe a consulta a qualquer
  chamador: aceito temporariamente (EPIC-006 é anterior à expansão de
  exposição); a lista/consulta por identificador deve ser revistada quando a
  autorização existir;
- R-04 — Divergência de contrato com o GET já existente (IMP-018): o DTO de
  resposta deve ser único e reaproveitado, evitando dois contratos
  concorrentes;
- R-05 — Busca por identificador institucional sem índice específico:
  mitigado pela constraint UNIQUE existente (índice único já criado na
  FEATURE-001);
- R-06 — Mudança futura do estado operacional (ex.: RA-009 PROVISIONING)
  alteraria o contrato de filtro/estado: isolado no Domain para que a
  transição seja transparente para a API.

---

# User Stories Candidatas

Identificação das histórias necessárias para a FEATURE-002 (a materializar
somente após aprovação do Discovery):

- US-009 — Consultar Tenant por ID (UC-001): obter dados institucionais,
  estado atual e data de criação de um Tenant conhecido;
- US-010 — Consultar Tenant por identificador institucional (UC-002):
  obter o Tenant a partir do dado estável da organização;
- US-011 — Listar Tenants (UC-003): relação paginada, ordenada e filtrável
  por estado operacional.

Critérios de aceitação transversais propostos:

- leitura sem efeitos colaterais e sem exposição de dados internos;
- 404 para Tenant inexistente;
- listagem paginada com ordenação determinística;
- consistência com o DTO único de resposta (R-04).

---

# Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 0.1.0 | 02/08/2026 | Primeira versão do Discovery da FEATURE-002 — Consultar Tenant, para revisão arquitetural. |
