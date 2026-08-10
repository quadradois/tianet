# US-068 - Priorizar Juros antes da Amortizacao

**ID:** US-068

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** responsavel financeiro,
**quero** que o Pagamento seja distribuido por regra oficial,
**para** preservar coerencia entre juros, encargos e amortizacao.

---

# 2. Critérios de Aceitação

- juros e encargos vencidos sao tratados antes da amortizacao do principal;
- a distribuicao e registrada em memoria de calculo;
- a regra aplicada e rastreavel;
- nenhuma outra camada redistribui Pagamento.

---

# 3. Regras de Negócio Relacionadas

- Pagamento e distribuido pelo Motor Financeiro;
- juros e encargos vencidos precedem amortizacao do principal.

---

# 4. Dependências

- FEATURE-025 - Registrar Pagamento;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

A regra pode evoluir por Configuracoes financeiras futuras.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Priorizar Juros antes da Amortizacao. |
