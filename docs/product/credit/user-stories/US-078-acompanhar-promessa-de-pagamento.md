# US-078 - Acompanhar Promessa de Pagamento

**ID:** US-078

**Versao:** 1.4.0

**Status:** Proposto

---

# 1. História

**Como** operador de cobranca autorizado,
**quero** acompanhar o resultado de uma promessa de pagamento,
**para** decidir a proxima acao operacional.

---

# 2. Critérios de Aceitação

- promessa `pendente` pode receber `pagamento_informado` antes do limite;
- `pendente` ou `pagamento_informado` passa a `descumprida` somente depois do
  limite, por reavaliacao sincronica ou pelo operador com justificativa;
- o resultado registra data, responsavel e justificativa quando aplicavel;
- promessa somente e marcada como cumprida quando um ou mais Pagamentos oficiais
  processados ou confirmados, e nao estornados, pertencem ao mesmo Tenant,
  Carteira e Emprestimo;
- quando a promessa referencia Parcela, somente valores oficialmente alocados a
  essa Parcela contribuem para o cumprimento;
- a soma elegivel deve atingir o valor declarado entre o registro da promessa e
  o fim da data prometida; pagamento insuficiente ou posterior nao a cumpre;
- cada fracao monetaria de Pagamento apropriada a uma promessa fica indisponivel
  para outras promessas; a soma das apropriacoes nunca excede o valor elegivel
  do Pagamento, ainda que ele seja rateado entre promessas;
- o estorno invalida as apropriacoes do Pagamento e reavalia todas as promessas
  afetadas; se a soma restante ficar insuficiente, a promessa volta a `pendente`
  ate o fim da data prometida ou passa a `descumprida` depois desse limite;
- Pagamento reconhecido posteriormente, mas recebido dentro da janela, pode
  corrigir `descumprida` para `cumprida`;
- a reavaliacao registra autoria sistemica, motivo e referencia ao estorno;
- `PromessaPagamentoCumprimentoInvalidado` e emitido uma unica vez apenas
  quando o estado anterior era `cumprida` e o novo e `pendente` ou
  `descumprida`; nao e emitido se continuar `cumprida` ou nunca esteve cumprida;
- o evento preserva `promessa_id`, `pagamento_id`, `estorno_id`, estados,
  motivo, instante, autoria, Tenant, Carteira, versao e chave idempotente;
- transicao repetida preserva o resultado sem duplicar historico;
- payload, data ou identificador malformado retorna `400`;
- promessa inexistente ou cross-tenant retorna `404` logico;
- transicao invalida, versao obsoleta ou fato idempotente divergente retorna `409`;
- acompanhar promessa nao registra Pagamento nem altera saldo.

---

# 3. Regras de Negócio Relacionadas

- Pagamento e confirmado exclusivamente pelo Motor Financeiro;
- estado da promessa representa acompanhamento operacional;
- a aplicacao valida escopo, operacao, valor, data e estado dos Pagamentos antes
  de aceitar a transicao para cumprida;
- apropriacao e invalidacao preservam trilha auditavel por Pagamento e promessa;
- `pagamento_informado` nao confirma nem registra Pagamento.

---

# 4. Dependências

- FEATURE-028 - Gerir Cobranca Manual;
- US-077 - Registrar Promessa de Pagamento;
- DOMAIN-012 - Evento Pagamento Registrado.
- EPIC-005 - produtor futuro de `PagamentoEstornadoV1`.

---

# 5. Observações Técnicas

`ApropriarPagamentoPromessa` associa explicitamente um Pagamento elegivel. Apos
essa apropriacao, ao consumir `PagamentoEstornadoV1` e antes de devolver uma
promessa vencida, `ReavaliarPromessaPagamento` materializa sincronicamente no
maximo uma transicao da DA-718, na mesma Unit of Work e com `data_referencia`
explicita. Descoberta automatica, batch e Scheduler ficam fora deste ciclo.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.4.0 | 2026-08-10 | Gatilhos sincronicos sem Scheduler e contrato HTTP completo formalizados. |
| 1.3.0 | 2026-08-10 | Maquina de estados completa, correcao retroativa e invalidacao condicional formalizadas. |
| 1.2.0 | 2026-08-10 | Apropriacao exclusiva e reavaliacao de promessa apos estorno formalizadas. |
| 1.1.0 | 2026-08-10 | Elegibilidade de Pagamentos para cumprimento da promessa formalizada apos revisao adversarial. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Acompanhar Promessa de Pagamento. |
