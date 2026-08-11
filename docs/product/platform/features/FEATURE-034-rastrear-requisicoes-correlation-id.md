# FEATURE-034 - Rastrear Requisicoes com Correlation ID

**ID:** FEATURE-034

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Garantir que toda requisicao HTTP tenha um correlation ID propagado para a
resposta, logs e tratamento tecnico de erros.

---

# 2. Valor de Negócio

Permitir que suporte e engenharia rastreiem uma falha reportada por cliente sem
depender de reproducao local.

---

# 3. Escopo

- aceitar `X-Correlation-ID` valido;
- gerar ID quando ausente ou invalido;
- devolver `X-Correlation-ID` em respostas 2xx, 4xx e 5xx;
- propagar o valor para logs da requisicao;
- preservar compatibilidade com IAM/RBAC.

---

# 4. Fora do Escopo

- tracing distribuido completo;
- correlacao entre servicos externos;
- identificacao de usuario sem autenticacao.

---

# 5. User Stories

- US-093 - Propagar Correlation ID HTTP;
- US-094 - Correlacionar Erros Tecnicos.

---

# 6. Dependências

- EPIC-008 - Fundacao Operacional e Observabilidade;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 7. Critérios de Aprovação

- requisicao sem header recebe ID gerado;
- requisicao com header valido preserva o valor;
- respostas de erro devolvem o mesmo correlation ID;
- logs incluem correlation ID.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature de correlation ID. |
