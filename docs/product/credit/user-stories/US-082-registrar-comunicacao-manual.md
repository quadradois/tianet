# US-082 - Registrar Comunicacao Manual

**ID:** US-082

**Versao:** 1.3.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** registrar uma comunicacao realizada manualmente,
**para** preservar o contexto do contato com o devedor.

---

# 2. Critérios de Aceitação

- o registro informa canal, data, responsavel e resultado;
- o registro exige Devedor e pode referenciar Emprestimo ou Cobranca que
  pertencam a esse Devedor, Tenant e Carteira;
- canal ou resultado ausente, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- cadeia visivel incompatível ou chave idempotente reutilizada com payload
  diferente retorna `409`, conforme DA-719;
- o Principal autenticado define a autoria;
- a mesma chave idempotente nao cria registro duplicado;
- o registro nao afirma envio ou entrega automatica.

---

# 3. Regras de Negócio Relacionadas

- Comunicacao e manual no MVP;
- registrar contato nao altera estado financeiro ou cadastral.

---

# 4. Dependências

- FEATURE-030 - Registrar Comunicacao Manual;
- EPIC-002 - Cadastro de Devedores;
- EPIC-006 - IAM.
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- PRODUCT-005 - Administrar Cobrancas;
- FEATURE-028 - Gerir Cobranca Manual.

---

# 5. Observações Técnicas

Integracoes com provedores e comprovantes de entrega ficam fora do EPIC-007.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.3.0 | 2026-08-10 | Conflito de chave idempotente com payload divergente formalizado. |
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 separado por causa. |
| 1.1.0 | 2026-08-10 | Cadeia referencial, dependencias e erros protegidos formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Registrar Comunicacao Manual. |
