# FEATURE-019 - Consultar Contratos

**ID:** FEATURE-019

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Consultar contratos de credito dentro da Carteira autenticada.

---

# 2. Valor de Negócio

Permite acompanhar contratos formalizados e suas transicoes sem acessar dados
financeiros do Motor futuro.

---

# 3. Escopo

- consultar contrato por ID;
- listar contratos por Carteira, Devedor, estado e periodo;
- consultar historico contratual;
- preservar paginacao e ordenacao deterministica;
- retornar 404 indistinguivel para recurso cross-tenant.

---

# 4. Fora do Escopo

- relatorios financeiros;
- saldo devedor;
- memoria de calculo;
- cobranca ou agenda.

---

# 5. User Stories

- US-055 - Consultar Contrato por ID;
- US-056 - Listar Contratos;
- US-058 - Consultar Historico Contratual.

---

# 6. Dependências

- EPIC-004 - Contratos de Credito;
- FEATURE-018 - Formalizar Contrato de Credito;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- consultas respeitam Tenant/Carteira;
- listagem possui filtros e paginacao;
- historico preserva transicoes auditaveis;
- leitura nao gera auditoria de escrita.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Consultar Contratos. |
