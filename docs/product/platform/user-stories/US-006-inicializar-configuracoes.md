# US-006 — Inicializar Configurações

**ID:** US-006

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** que as configurações padrão sejam aplicadas na criação da organização

**Para** que o Tenant nasça operacional, sem exigir parametrização manual inicial.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o conjunto de configurações padrão for aplicado automaticamente no provisionamento;
- cada configuração pertencer ao Tenant provisionado;
- a chave de configuração for única por Tenant;
- as configurações forem persistidas na mesma transação do provisionamento;
- a falha na aplicação impedir o provisionamento inteiro.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-017 — Aggregate Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- US-001 — Criar Tenant;
- US-005 — Criar Usuário Administrador.

---

# 5. Observações Técnicas

Trata-se das **Configurações da Plataforma** (parâmetros do Tenant), distintas
das Configurações Financeiras (taxas, modalidades, calendário) previstas para o
contexto de Operações de Crédito — desambiguação registrada no
ROADMAP-ALIGNMENT.

O conjunto padrão é mínimo no MVP e evoluirá quando houver Discovery próprio.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
