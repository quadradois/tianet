# FEATURE-028 - Gerir Cobranca Manual

**ID:** FEATURE-028

**Versao:** 1.4.0

**Status:** Proposto

---

# 1. Objetivo

Organizar o acompanhamento manual de operacoes que exigem acao de cobranca e
registrar seu historico operacional.

---

# 2. Valor de Negócio

Permite priorizar o trabalho de recuperacao de credito e preservar evidencias
de cada contato e compromisso assumido pelo devedor.

---

# 3. Escopo

- consultar fila de cobranca por periodo e situacao oficial;
- registrar acao de cobranca com responsavel e resultado;
- registrar promessa de pagamento com data e valor informados;
- acompanhar promessa conforme a tabela de estados DA-718;
- referenciar Emprestimo, derivar Devedor e validar Parcela quando aplicavel;
- auditar escritas e aplicar isolamento por Tenant/Carteira.

---

# 4. Fora do Escopo

- recalcular inadimplencia, saldo, juros ou quitacao;
- renegociar a operacao;
- alterar vencimento ou plano de Parcelas;
- executar cobranca automatica ou juridica.

---

# 5. User Stories

- US-075 - Consultar Fila de Cobranca;
- US-076 - Registrar Acao de Cobranca;
- US-077 - Registrar Promessa de Pagamento;
- US-078 - Acompanhar Promessa de Pagamento.

---

# 6. Dependências

- EPIC-007 - Operacao Diaria;
- PRODUCT-005 - Administrar Cobrancas;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-002 - Cadastro de Devedores;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- fila apresenta apenas recursos autorizados da Carteira corrente;
- valores e situacoes financeiras exibidos vem de `SituacaoParcelaNaDataV1` do
  Motor;
- acao e promessa registram autoria, data e referencias;
- promessa nao altera Contrato, Emprestimo ou Parcela;
- promessa somente fica cumprida com Pagamentos oficiais nao estornados do mesmo
  Tenant, Carteira e Emprestimo, recebidos ate a data prometida e cuja soma
  elegivel alcance o valor declarado;
- promessa vinculada a Parcela considera somente valores oficialmente alocados
  a essa Parcela;
- cada valor de Pagamento apropriado e consumido no maximo uma vez entre
  promessas, admitindo rateio sem exceder o valor elegivel do Pagamento;
- estorno invalida apropriacoes, reavalia promessas afetadas e registra o motivo
  sem alterar qualquer fato financeiro do Motor;
- `PromessaPagamentoCumprimentoInvalidado` somente e emitido quando uma promessa
  `cumprida` passa a `pendente` ou `descumprida`;
- `ApropriarPagamentoPromessa` associa o Pagamento explicitamente e a promessa e
  reavaliada sincronicamente apos apropriacao, estorno ou leitura vencida, com
  `data_referencia` e sem descoberta automatica ou Scheduler obrigatorio;
- formato, payload, data ou identificador malformado retorna `400`;
- referências visiveis de cadeias diferentes retornam `409`, enquanto recurso
  inexistente ou cross-tenant retorna `404` logico;
- repeticao da mesma escrita idempotente nao cria duplicidade;
- tentativas cross-tenant retornam `404` logico.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.4.0 | 2026-08-10 | Reavaliacao sincronica sem Scheduler e contrato HTTP completo formalizados. |
| 1.3.0 | 2026-08-10 | Maquina de estados, invalidacao condicional e integridade referencial formalizadas. |
| 1.2.0 | 2026-08-10 | Apropriacao exclusiva e reavaliacao de promessas apos estorno formalizadas. |
| 1.1.0 | 2026-08-10 | Regra de elegibilidade do Pagamento para cumprimento de promessa formalizada. |
| 1.0.0 | 2026-08-10 | Primeira versao da Feature Gerir Cobranca Manual. |
