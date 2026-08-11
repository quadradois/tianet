# US-088 - Impedir Calculo Financeiro fora do Motor na Operacao Diaria

**ID:** US-088

**Versao:** 1.1.0

**Status:** Proposto

---

# 1. História

**Como** arquiteto da plataforma,
**quero** impedir calculo financeiro definitivo na Operacao Diaria,
**para** preservar o Motor Financeiro como fonte unica da verdade.

---

# 2. Critérios de Aceitação

- guardrails cobrem Cobranca, Agenda, Comunicacao e Relatorios;
- nenhum modulo do EPIC-007 calcula juros, mora, multa, amortizacao, saldo,
  quitacao ou memoria de calculo;
- nenhum modulo financeiro usa `float`;
- promessa de pagamento nao altera fato financeiro;
- relatorios consomem valores oficiais ou projecoes rastreaveis do Motor;
- `count`, `sum` e `group` sobre campos oficiais, filtros e comparacoes de
  datas/estados sao permitidos;
- soma de apropriacoes oficiais para cumprimento de promessa e permitida;
- recertificacao falha diante de juros, mora, multa, amortizacao, saldo,
  quitacao, arredondamento monetario ou memoria de calculo fora do Motor.

---

# 3. Regras de Negócio Relacionadas

- Motor Financeiro e a unica autoridade de calculo definitivo;
- contextos downstream organizam e projetam fatos sem recomputar valores.

---

# 4. Dependências

- FEATURE-031 - Consultar Relatorios Operacionais;
- EPIC-007 - Operacao Diaria;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- US-074 - Impedir Calculo Financeiro fora do Motor.

---

# 5. Observações Técnicas

O PLAN tecnico deve prever testes AST positivos para agregacoes permitidas e
negativos para formulas proibidas em todos os modulos do EPIC-007. Nomes
alternativos ou expressoes inline nao podem contornar o guardrail.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-10 | Allowlist de agregacoes e denylist de formulas financeiras formalizadas. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story de guardrail da Operacao Diaria. |
