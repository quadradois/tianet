# US-058 - Consultar Historico Contratual

**ID:** US-058

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuario autorizado

**Quero** consultar o historico contratual

**Para** auditar criacao, assinatura, liberacao, cancelamento ou encerramento.

---

# 2. Critérios de Aceitação

- historico mostra transicoes, ator, motivo opcional e instante;
- consulta respeita Tenant/Carteira;
- recurso cross-tenant retorna 404;
- historico e append-only;
- leitura nao altera o contrato.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-019 - Consultar Contratos;
- FEATURE-020 - Registrar Assinatura Contratual;
- EPIC-004 - Contratos de Credito;
- ADR-002 - Auditoria Independente da Transacao.

---

# 4. Dependências

- FEATURE-019 - Consultar Contratos;
- FEATURE-020 - Registrar Assinatura Contratual;
- ADR-002 - Auditoria Independente da Transacao.

---

# 5. Observações Técnicas

Historico contratual deve ser append-only e filtrado pelo mesmo isolamento do
contrato consultado.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Consultar Historico Contratual. |
