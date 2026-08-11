# FEATURE-022 - Cancelar ou Encerrar Contrato

**ID:** FEATURE-022

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Permitir cancelamento ou encerramento administrativo de contratos conforme seu
estado.

---

# 2. Valor de Negócio

Permite interromper ou fechar o ciclo documental sem confundir contrato com
operacao financeira.

---

# 3. Escopo

- cancelar contrato ainda nao liberado;
- encerrar contrato sem alterar operacao financeira;
- registrar motivo, ator e instante;
- auditar transicoes;
- impedir alteracoes indevidas em contrato liberado.

---

# 4. Fora do Escopo

- liquidar Emprestimo;
- quitar saldo;
- renegociar operacao financeira;
- cancelar pagamento ou parcela.

---

# 5. User Stories

- US-061 - Cancelar Contrato nao Liberado;
- US-062 - Encerrar Contrato sem Alterar Operacao Financeira.

---

# 6. Dependências

- EPIC-004 - Contratos de Credito;
- FEATURE-018 - Formalizar Contrato de Credito.

---

# 7. Critérios de Aprovação

- cancelamento respeita estados permitidos;
- encerramento nao altera entidades financeiras;
- transicoes invalidas retornam conflito;
- auditoria registra motivo, ator e instante.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Cancelar ou Encerrar Contrato. |
