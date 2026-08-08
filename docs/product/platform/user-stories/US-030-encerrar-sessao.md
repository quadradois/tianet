# US-030 — Encerrar Sessão

**ID:** US-030

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuário operador do Tenant

**Quero** encerrar minha sessão

**Para** impedir que ela seja renovada por quem quer que tenha acesso ao meu refresh token.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o encerramento revogar o refresh token da sessão;
- o refresh token revogado não permitir mais renovação, respondendo 401;
- o token de acesso já emitido **permanecer válido até expirar** — no máximo 15 minutos —, consequência aceita e registrada na ADR-004;
- encerrar uma sessão já encerrada não produzir erro (operação idempotente);
- o encerramento afetar apenas a sessão apresentada, e não as demais sessões do mesmo Usuário em outros dispositivos;
- o encerramento ser registrado na trilha de auditoria append-only (ADR-002).

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- ADR-004 — Autenticação e Autorização (IAM): o token de acesso é autocontido, logo não é revogável antes de expirar; a revogação atua sobre o refresh token;
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-018 — Entity Usuario;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- FEATURE-009 — Autenticar Usuário.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-009 — Autenticar Usuário;
- US-028 — Autenticar com Credencial;
- US-029 — Renovar Token de Acesso;
- EPIC-006 — IAM (Identidade e Controle de Acesso);
- ADR-004 — Autenticação e Autorização (IAM).

---

# 5. Observações Técnicas

Encerrar sessão não é o mesmo que cortar o acesso instantaneamente. O token de
acesso continua válido até expirar, porque não é consultado no banco — foi essa
a escolha registrada na ADR-004, e a janela de 15 minutos é exatamente o preço
dela.

Quando for necessário cortar o acesso de imediato, a via não é esta User Story:
seria uma verificação por requisição, decisão que a ADR-004 descartou por anular
a razão de ser do JWT.

O escopo é a sessão apresentada. Revogar todas as sessões de um Usuário é efeito
colateral de outras operações — alteração de credencial (US-033) e redefinição
administrativa (US-034) —, não desta.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Primeira versão oficial da User Story Encerrar Sessão. |
