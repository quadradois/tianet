# US-093 - Propagar Correlation ID HTTP

**ID:** US-093

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** suporte da plataforma,

**Quero** que toda resposta HTTP devolva um correlation ID,

**Para** localizar nos logs a requisicao reportada pelo cliente.

---

# 2. Critérios de Aceitação

- requisicao sem `X-Correlation-ID` recebe ID gerado;
- requisicao com `X-Correlation-ID` valido preserva o valor;
- valor invalido e substituido por ID seguro;
- respostas 2xx, 4xx e 5xx incluem `X-Correlation-ID`;
- logs da requisicao contem o mesmo ID.

---

# 3. Regras de Negócio Relacionadas

- correlation ID nao autentica nem autoriza usuario;
- correlation ID nao pode carregar dado sensivel.

---

# 4. Dependências

- FEATURE-034 - Rastrear Requisicoes com Correlation ID;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 5. Observações Técnicas

O contrato deve ser implementado na borda HTTP para cobrir endpoints protegidos
e o healthcheck publico.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de correlation ID HTTP. |
