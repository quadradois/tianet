# US-017 — Validar Unicidade do Documento

**ID:** US-017

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor (usuário do Tenant)

**Quero** que o documento (CPF) do Devedor seja único na minha Carteira

**Para** impedir cadastros duplicados e manter a rastreabilidade do relacionamento de crédito.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema verificar a ausência do documento na Carteira antes da criação;
- documento já cadastrado (Ativo ou Inativo) retornar 409;
- a verificação considerar apenas a Carteira do Tenant (isolamento);
- corridas concorrentes de criação com o mesmo documento resultarem em um único cadastro.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- DOMAIN-024 — Business Rule Documento Único por Carteira;
- DOMAIN-023 — Domain Service UnicidadeDevedorService;
- DOMAIN-020 — Aggregate Devedor (INV-002);
- FEATURE-005 — Criar Devedor.

---

# 4. Dependências

Esta User Story depende de:

- US-015 — Criar Devedor;
- US-016 — Validar Dados Obrigatórios do Devedor;
- FEATURE-005 — Criar Devedor.

---

# 5. Observações Técnicas

Unicidade em duas camadas: Domain (UnicidadeDevedorService) e constraint UNIQUE no repositório para proteção contra corrida (padrão FEATURE-001 IMP-008/IMP-021).

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da User Story Validar Unicidade do Documento. |