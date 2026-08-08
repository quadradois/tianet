# US-005 — Criar Usuário Administrador

**ID:** US-005

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** que um Usuário administrador seja criado junto com a organização

**Para** que exista desde o início um responsável habilitado a operar o Tenant.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o nome e o e-mail do administrador informados na criação originarem o Usuário;
- o Usuário for criado na mesma transação do provisionamento;
- o Usuário pertencer obrigatoriamente ao Tenant provisionado;
- a falha na criação do Usuário impedir o provisionamento inteiro;
- nenhuma credencial de acesso for definida nesta etapa.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-018 — Entity Usuario;
- DOMAIN-017 — Aggregate Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- US-001 — Criar Tenant;
- US-004 — Criar Carteira Padrão.

---

# 5. Observações Técnicas

Autenticação e credenciais estão **fora do escopo** desta User Story e do
EPIC-001: pertencem ao EPIC-006 (IAM). Aqui o Usuário é apenas registrado como
entidade do Tenant.

O perfil de acesso existe no modelo como atributo, sem semântica de autorização
até que o IAM seja implementado.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
