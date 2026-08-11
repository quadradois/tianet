# US-087 - Consultar Fluxo Previsto e Realizado

**ID:** US-087

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** gestor autorizado,
**quero** comparar fluxo previsto e realizado por periodo,
**para** acompanhar a execucao financeira da Carteira.

---

# 2. Critérios de Aceitação

- previsto deriva do plano oficial de Parcelas;
- realizado soma `valor_efeito_realizado_assinado` dos fatos oficiais do Motor;
- Pagamento e estorno entram pela data oficial de seus efeitos, sem regra local
  de compensacao;
- periodo, Carteira e data de referencia ficam explicitos;
- os totais permitem rastrear os fatos que os compoem;
- a consulta nao projeta cenarios nem recalcula juros;
- apenas dados do escopo autorizado sao agregados;
- filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- `409` nao se aplica enquanto a consulta nao combinar referencias
  independentes nem transicionar estado, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- fluxo previsto e realizado e uma leitura de fatos do Motor;
- previsao analitica ou preditiva fica fora do MVP.

---

# 4. Dependências

- FEATURE-031 - Consultar Relatorios Operacionais;
- US-084 - Consultar Resumo da Carteira;
- US-086 - Consultar Pagamentos e Operacoes Encerradas.

---

# 5. Observações Técnicas

Read model deve preservar data de atualizacao e possibilidade de rebuild.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP aplicavel de DA-719 formalizado. |
| 1.1.0 | 2026-08-10 | Fluxo realizado por efeitos assinados e estornos rastreaveis formalizado. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Fluxo Previsto e Realizado. |
