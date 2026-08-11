# US-080 - Criar Compromisso e Lembrete

**ID:** US-080

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** criar um compromisso ou lembrete,
**para** registrar o proximo passo de acompanhamento.

---

# 2. Critérios de Aceitação

- o item informa data, responsavel, prioridade e descricao;
- o item pode referenciar Devedor, Emprestimo, Caso de Cobranca ou promessa;
- todas as referencias fornecidas resolvem para a mesma cadeia Tenant, Carteira,
  Devedor e Emprestimo por contrato/ACL;
- compromisso ou lembrete nasce com estado `aberto`;
- formato, payload, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- referencias visiveis de cadeias diferentes ou chave idempotente reutilizada
  com payload diferente retornam `409`;
- o Principal autenticado define a autoria;
- a mesma chave idempotente nao cria item duplicado;
- criar item nao dispara notificacao externa.

---

# 3. Regras de Negócio Relacionadas

- compromisso e lembrete sao fatos operacionais;
- item de Agenda nao cria nem altera obrigacao financeira.

---

# 4. Dependências

- FEATURE-029 - Administrar Agenda Operacional;
- PRODUCT-006 - Administrar Agenda;
- US-079 - Consultar Agenda Operacional.
- PRODUCT-005 - Administrar Cobrancas;
- FEATURE-028 - Gerir Cobranca Manual;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

O MVP permite processamento manual; automacao por Scheduler e posterior.
Referencias a Cobranca sao opcionais e atravessam contrato/ACL.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Conflito de chave idempotente com payload divergente formalizado. |
| 1.1.0 | 2026-08-10 | Estado inicial, cadeia referencial, dependencias e erros protegidos formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Criar Compromisso e Lembrete. |
