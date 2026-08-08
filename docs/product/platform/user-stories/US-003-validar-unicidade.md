# US-003 — Validar Unicidade

**ID:** US-003

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** que o identificador institucional seja único na plataforma

**Para** impedir que duas organizações distintas compartilhem a mesma identidade.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o identificador institucional for único entre todos os Tenants;
- a tentativa de criar organização com identificador já existente for rejeitada;
- a verificação ocorrer por serviço de domínio antes da persistência;
- a unicidade for garantida também por constraint no banco, protegendo contra corridas concorrentes;
- a violação retornar conflito, sem criar recursos parciais.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-017 — Aggregate Tenant;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- US-001 — Criar Tenant;
- US-002 — Validar Dados Obrigatórios.

---

# 5. Observações Técnicas

A checagem em memória por serviço de domínio não substitui a constraint única no
banco: duas requisições simultâneas passariam pela verificação e apenas a
constraint impediria a duplicação.

A violação de unicidade é traduzida para conflito na camada Presentation.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
