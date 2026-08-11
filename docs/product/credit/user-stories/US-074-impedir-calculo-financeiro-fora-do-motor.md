# US-074 - Impedir Calculo Financeiro fora do Motor

**ID:** US-074

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** arquiteto da plataforma,
**quero** impedir calculo financeiro definitivo fora do Motor,
**para** preservar o Core Domain e a fonte unica da verdade.

---

# 2. Critérios de Aceitação

- guardrails detectam calculo financeiro em Comercial, Contratos e downstreams;
- nenhum endpoint calcula saldo, juros, amortizacao ou quitacao fora do Motor;
- testes falham se `float` aparecer em regra financeira;
- relatorio de recertificacao lista evidencias da exclusividade do Motor.

---

# 3. Regras de Negócio Relacionadas

- calculo financeiro definitivo pertence exclusivamente ao Motor Financeiro;
- Comercial, Contratos e downstreams nao calculam juros, saldo, amortizacao ou
  quitacao.

---

# 4. Dependências

- FEATURE-027 - Quitar e Renegociar Operacao;
- FOUNDATION-004 - Core Domain;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Guardrail deve combinar busca estrutural e testes de regressao.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Impedir Calculo Financeiro fora do Motor. |
