# US-029 — Renovar Token de Acesso

**ID:** US-029

**Versão:** 1.0.0

**Status:** Concluido

---

# 1. História

**Como** Usuário operador do Tenant

**Quero** renovar meu token de acesso apresentando o refresh token

**Para** continuar operando sem informar minha credencial a cada quinze minutos.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- um refresh token válido e não revogado produzir um novo token de acesso com validade de 15 minutos;
- a renovação não exigir a credencial do Usuário;
- refresh token expirado (mais de 7 dias) não renovar e receber 401;
- refresh token revogado — por encerramento de sessão, alteração de credencial ou inativação do Tenant — não renovar e receber 401;
- o novo token de acesso carregar o mesmo Usuário e Tenant do refresh apresentado;
- o Perfil embutido no novo token refletir o Perfil vigente no momento da renovação, e não o do login original;
- a renovação ser registrada na trilha de auditoria append-only (ADR-002).

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): o refresh é persistido e revogável; Tenant e Usuário inativos também impedem imediatamente a resolução do Principal;
- ADR-001 — Stack Tecnológica Oficial do MVP: JWT (Bearer) + Refresh Token;
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuario;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- FEATURE-009 — Autenticar Usuário.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-009 — Autenticar Usuário;
- US-028 — Autenticar com Credencial;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- ADR-004 — Autenticação e Autorização (IAM).

---

# 5. Observações Técnicas

A renovação é o ponto de controle do sistema. Como o token de acesso é
autocontido e não é consultado no banco, é aqui — e somente aqui — que uma
revogação passa a ter efeito observável. Essa é a razão de a validade do token
de acesso ser curta: ela define quanto tempo um acesso revogado ainda funciona.

A verificação do refresh token exige consulta ao armazenamento, ao contrário da
validação do token de acesso. Reavaliar o Perfil na renovação faz com que
mudanças de permissão também se propaguem dentro da mesma janela.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Renovar Token de Acesso. |
