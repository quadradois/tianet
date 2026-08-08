# US-031 — Recusar Autenticação Inválida

**ID:** US-031

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Sistema

**Quero** recusar tentativas de autenticação com credencial incorreta, identificador inexistente ou Usuário não-Ativo com a mesma resposta genérica

**Para** não revelar se um identificador existe nem o motivo da recusa, impedindo a enumeração de Usuários e a exposição do estado do cadastro a quem não deveria conhecê-lo.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- credencial incorreta para um Usuário Ativo retornar HTTP 401 com a resposta genérica de autenticação recusada;
- identificador inexistente retornar a mesma resposta genérica com o mesmo código HTTP 401, sem qualquer indicação de que o identificador não existe;
- Usuário existente porém não-Ativo (Convidado, Inativo ou Removido) retornar a mesma resposta genérica com o mesmo código HTTP 401, sem revelar o estado do Usuário;
- a resposta não distinguir entre identificador desconhecido e senha incorreta, usando corpo e mensagem idênticos em todos os cenários de recusa;
- a credencial nunca aparecer em texto legível na resposta, em log ou na trilha de auditoria;
- toda tentativa recusada ser registrada na trilha de auditoria append-only (ADR-002), com o identificador apresentado e o momento da tentativa;
- o mesmo fluxo de recusa genérica se aplicar também quando a credencial estiver em formato inválido, sem revelar se o identificador existe.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM), contrato de erro 401 para sem token válido e sigilo do motivo da recusa;
- DOMAIN-017 — Aggregate Tenant (INV de isolamento: o acesso nunca atravessa a fronteira de Tenant);
- DOMAIN-018 — Entity Usuario (INV-001: Usuário pertence a exatamente um Tenant; apenas o estado Ativo autentica);
- ADR-002 — Auditoria Independente da Transação (eventos de acesso na trilha append-only);
- ADR-018 — Identidade Externa do Devedor (precedente de não revelar existência);
- FOUNDATION-006 — Arquitetura Multi-Tenant (isolamento verificado, nunca revelado por contraste de erro);
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-006 — IAM — Identidade e Controle de Acesso;
- FEATURE-009 — Autenticar Usuário.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-009 — Autenticar Usuário;
- EPIC-006 — IAM — Identidade e Controle de Acesso;
- PRODUCT-001 — Capability Administrar Plataforma;
- ADR-004 — Autenticação e Autorização (IAM).

---

# 5. Observações Técnicas

A recusa genérica é um contrato de segurança: o código HTTP 401 e o corpo da resposta devem ser idênticos entre credencial incorreta, identificador inexistente, Usuário não-Ativo e formato inválido de credencial. Não basta corpo igual — o tempo de processamento de cada cenário também deve ser uniforme, para não criar um vetor de inferência por timing.

O estado Ativo é pré-requisito de autenticação: Usuário em qualquer outro estado segue o mesmo caminho de recusa genérica, sem indicar o estado.

A tentativa recusada é um evento de acesso auditado na trilha append-only (ADR-002), registrando o identificador apresentado e o momento, nunca a credencial.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Recusar Autenticação Inválida. |
