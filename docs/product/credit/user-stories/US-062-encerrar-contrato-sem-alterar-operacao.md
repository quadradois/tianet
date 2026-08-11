# US-062 - Encerrar Contrato sem Alterar Operacao Financeira

**ID:** US-062

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuario autorizado

**Quero** encerrar administrativamente um contrato

**Para** refletir seu ciclo documental sem alterar Emprestimos, Parcelas ou
Pagamentos.

---

# 2. Critérios de Aceitação

- encerramento registra ator, motivo e instante;
- encerramento nao calcula saldo nem quitacao;
- encerramento nao altera Emprestimo, Parcela ou Pagamento;
- transicao invalida retorna 409;
- auditoria preserva a trilha.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-022 - Cancelar ou Encerrar Contrato;
- EPIC-004 - Contratos de Credito;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro futuro.

---

# 4. Dependências

- FEATURE-022 - Cancelar ou Encerrar Contrato;
- EPIC-004 - Contratos de Credito.

---

# 5. Observações Técnicas

Encerramento contratual nao substitui quitacao, liquidacao ou renegociacao do
Motor Financeiro.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Encerrar Contrato sem Alterar Operacao Financeira. |
