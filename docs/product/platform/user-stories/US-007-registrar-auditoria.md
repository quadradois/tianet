# US-007 — Registrar Auditoria

**ID:** US-007

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** que cada etapa do provisionamento seja registrada em trilha de auditoria

**Para** poder reconstituir o que aconteceu, inclusive quando a criação falha.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- cada etapa do provisionamento gerar um evento na trilha;
- a trilha registrar início, dados validados, carteira criada, usuário criado, configurações aplicadas, confirmação e sucesso;
- falhas registrarem os eventos de falha e de rollback;
- a trilha for **append-only** e imutável;
- os registros de falha e rollback **sobreviverem ao rollback** da transação de negócio;
- a leitura da trilha não gerar novos eventos.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-017 — Aggregate Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- US-001 — Criar Tenant.

---

# 5. Observações Técnicas

A trilha usa **sessão independente** da transação de negócio (ADR-002): é isso
que permite ao registro de falha sobreviver ao rollback. Gravar na mesma sessão
apagaria justamente a evidência do que deu errado.

Somente operações de escrita são auditadas; consultas não geram trilha.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
