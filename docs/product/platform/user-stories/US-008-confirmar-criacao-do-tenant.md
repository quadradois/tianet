# US-008 — Confirmar Criação do Tenant

**ID:** US-008

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** receber a confirmação da organização criada com seu estado final

**Para** ter certeza de que o provisionamento foi concluído por inteiro.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- a confirmação ocorrer somente após todas as etapas do provisionamento;
- o Tenant transitar de Provisão para **Ativo** antes da resposta;
- a resposta trazer identidade, identificador institucional, nome, estado e data de criação;
- a resposta utilizar DTO específico da camada Presentation, sem expor o Aggregate;
- o reenvio da mesma Idempotency-Key retornar exatamente o mesmo resultado, sem criar novos recursos;
- o commit ocorrer apenas ao final, com rollback automático em caso de falha.

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
- US-006 — Inicializar Configurações;
- US-007 — Registrar Auditoria.

---

# 5. Observações Técnicas

A transição para Ativo é decidida pelo Aggregate (DOMAIN-017), não pela camada de
Aplicação.

A idempotência (AD-002) é identificada pelo par chave + escopo do caso de uso:
a mesma chave em operações distintas designa operações distintas.

A resposta usa DTO próprio da Presentation — o Aggregate nunca é serializado
diretamente.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
