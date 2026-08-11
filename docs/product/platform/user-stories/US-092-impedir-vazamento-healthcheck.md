# US-092 - Impedir Vazamento no Healthcheck

**ID:** US-092

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** responsavel por seguranca,

**Quero** que o healthcheck exponha somente informacao operacional minima,

**Para** evitar vazamento de credenciais, configuracoes internas ou dados sensiveis.

---

# 2. Critérios de Aceitação

- resposta nao contem DSN, senha, segredo, token, stack trace ou variavel sensivel;
- resposta nao revela Tenant, Usuario, Carteira ou dado financeiro;
- erro interno de dependencia nao devolve detalhe bruto ao cliente;
- testes negativos cobrem termos sensiveis conhecidos.

---

# 3. Regras de Negócio Relacionadas

- resposta publica deve ser minima;
- seguranca operacional prevalece sobre detalhamento de diagnostico publico.

---

# 4. Dependências

- FEATURE-033 - Validar Saude Operacional do Backend;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 5. Observações Técnicas

Detalhes tecnicos devem ir para logs seguros com correlation ID, nao para o
payload publico do healthcheck.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de healthcheck seguro. |
