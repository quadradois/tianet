# FEATURE-020 - Registrar Assinatura Contratual

**ID:** FEATURE-020

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Registrar assinatura ou formalizacao contratual no MVP.

---

# 2. Valor de Negócio

Garante evidencia minima de concordancia antes de liberar o contrato para a
proxima etapa operacional.

---

# 3. Escopo

- registrar ator, instante e evidencias internas de assinatura;
- mover contrato para estado assinado/formalizado;
- impedir assinatura de contrato cancelado, encerrado ou liberado;
- auditar a transicao.

---

# 4. Fora do Escopo

- assinatura digital externa;
- biometria;
- integracao com provedores de documento;
- armazenamento de arquivo contratual.

---

# 5. User Stories

- US-057 - Registrar Assinatura Contratual;
- US-058 - Consultar Historico Contratual.

---

# 6. Dependências

- EPIC-004 - Contratos de Credito;
- FEATURE-018 - Formalizar Contrato de Credito.

---

# 7. Critérios de Aprovação

- assinatura altera estado conforme transicao valida;
- transicao invalida responde conflito;
- auditoria preserva ator e instante;
- nenhuma integracao externa e exigida no MVP.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Registrar Assinatura Contratual. |
