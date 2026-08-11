# EPIC-007 - Discovery/SDD de Operacao Diaria

**ID:** EPIC-007

**Tipo:** Artefato de Discovery/SDD

**Versao:** 1.6.0

**Status:** Aprovado para planejamento

---

# 1. Objetivo

Este discovery prepara o ciclo do EPIC-007 - Operacao Diaria, contemplando
Cobranca, Agenda, Comunicacao manual e Relatorios basicos.

O objetivo e definir escopo, fronteiras, eventos de entrada, riscos, contratos
de integracao e plano inicial de testes antes de criar codigo. O EPIC-007 nasce
como camada operacional downstream do Motor Financeiro: ele acompanha, organiza,
notifica internamente e consolida fatos, mas nao calcula juros, saldo,
amortizacao, quitacao ou memoria financeira definitiva.

---

# 2. Autoridades Consultadas

- `docs/foundation/FOUNDATION-005-inventario-do-dominio.md`;
- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md`;
- `docs/audits/discoveries/EPIC-005-motor-financeiro-discovery.md`;
- `docs/implementation/plans/PLAN-013-epic-005-motor-financeiro.md`;
- `docs/domain/credit/events/DOMAIN-011-event-emprestimo-criado.md`;
- `docs/domain/credit/events/DOMAIN-012-event-pagamento-registrado.md`;
- `docs/domain/credit/events/DOMAIN-013-event-emprestimo-quitado.md`.

---

# 3. Contexto

O MVP ja possui a cadeia principal de credito ate o Motor Financeiro:

1. Platform/IAM garantem tenant, usuario autenticado e RBAC.
2. Cadastro fornece Devedor.
3. Comercial cria simulacoes e propostas.
4. Contratos formaliza e libera logicamente a operacao.
5. Motor Financeiro cria Emprestimo, Parcelas, Pagamentos, Quitacao,
   Renegociacao e Memoria de Calculo.

O EPIC-007 fecha o uso operacional diario dessa cadeia. Ele transforma fatos
financeiros e cadastrais em rotinas de acompanhamento: cobrancas manuais,
compromissos, retornos, historico de comunicacao e indicadores basicos.

Ha uma divergencia historica em documentos antigos que associavam Cobranca,
Agenda, Comunicacao e Relatorios ao EPIC-005. O roadmap consolidado em
`ROADMAP-ALIGNMENT-PRODUCT-AMP.md` e `AMP-001` posiciona esse pacote como
**EPIC-007 - Operacao Diaria**, apos o Motor Financeiro.

---

# 4. Escopo

O EPIC-007 contempla:

- acompanhar vencimentos e parcelas pendentes a partir de fatos do Motor;
- identificar operacoes que exigem acao de cobranca manual;
- registrar acao de cobranca realizada pelo usuario;
- registrar promessa de pagamento sem alterar condicoes financeiras;
- criar e consultar compromissos de Agenda;
- registrar lembretes e retornos operacionais;
- registrar comunicacoes manuais com devedor;
- manter historico de comunicacao por devedor/emprestimo;
- expor consultas operacionais por tenant/carteira;
- produzir relatorios basicos de carteira, vencimentos, inadimplencia,
  pagamentos e operacoes encerradas;
- proteger endpoints por IAM/RBAC;
- documentar contratos OpenAPI e erros HTTP;
- manter guardrails para impedir calculo financeiro definitivo fora do Motor.

---

# 5. Fora do Escopo

Este Epic nao contempla:

- calculo de juros, multa, mora, amortizacao, saldo ou quitacao;
- alteracao de plano de parcelas por Cobranca ou Agenda;
- renegociacao financeira fora do Motor Financeiro;
- disparo automatico de WhatsApp, SMS, e-mail ou push;
- integracao com provedores externos de mensageria;
- cobranca automatica, robo de cobranca ou workflows temporizados complexos;
- integracao bancaria, PIX, boleto ou conciliacao;
- protesto, negativacao, registro de divida ou cobranca juridica;
- BI avancado, data lake, analytics preditivo ou machine learning;
- front-end operacional.

---

# 6. Fronteiras

| Contexto | Relacao com EPIC-007 | Regra de fronteira |
|---|---|---|
| Platform | Upstream transversal | fornece Tenant, Carteira e isolamento. |
| IAM | Upstream transversal | autentica usuario e autoriza acoes por RBAC. |
| Cadastro | Upstream | fornece Devedor, contatos e dados cadastrais. |
| Contratos | Upstream direto de Relatorios | fornece encerramento e cancelamento administrativos, que nao pertencem ao Motor. |
| Motor Financeiro | Upstream direto | fonte oficial de Emprestimo, Parcelas, Pagamentos, Saldos, Quitacao, vencimento e inadimplencia. |
| Cobranca | Contexto operacional | registra acompanhamento, acao manual e promessa sem recalcular. |
| Agenda | Contexto operacional | organiza vencimentos, compromissos, lembretes e retornos. |
| Comunicacao | Contexto operacional | registra historico manual de contato, sem envio externo no MVP. |
| Relatorios | Contexto de leitura | consolida fatos e read models sem comandar transicoes. |
| Scheduler | Futuro | nao e prerequisito para o MVP manual do EPIC-007. |
| Notification | Futuro | envio automatico fica fora do MVP. |
| Event Bus | Futuro/tecnico | pode ser substituido inicialmente por projecoes sincronas/rebuild. |

---

# 7. Entradas e Saidas Candidatas

## 7.1 Entradas do Motor Financeiro

- `EmprestimoCriado`;
- `ParcelasGeradas`;
- `PagamentoRegistrado`;
- `PagamentoEstornado`;
- `SaldoCalculado`;
- `ValorQuitacaoCalculado`;
- `EmprestimoQuitado`;
- `EmprestimoRenegociado`.

No MVP sem Event Bus, essas entradas podem ser consumidas por consulta ou
projecao sincrona no mesmo PostgreSQL, desde que preservem identidade, versao e
idempotencia do fato de origem.

## 7.2 Entradas de Cadastro

- `DevedorCadastrado`;
- `DevedorAtualizado`;
- `DevedorInativado`;
- `DevedorReativado`.

## 7.3 Entradas de Contratos

- `ContratoEncerradoAdministrativamente`;
- `ContratoCancelado`.

## 7.4 Saidas do EPIC-007

- `AcaoCobrancaRegistrada`;
- `PromessaPagamentoRegistrada`;
- `PromessaPagamentoCumprida`;
- `PromessaPagamentoCumprimentoInvalidado`;
- `PromessaPagamentoDescumprida`;
- `CompromissoAgendaCriado`;
- `CompromissoAgendaConcluido`;
- `LembreteRegistrado`;
- `ComunicacaoManualRegistrada`.

Consultas de Relatorios nao produzem evento de dominio nem registro em
`audit_log`, conforme ADR-002. Logs tecnicos de observabilidade, quando
existirem, nao constituem trilha de auditoria de negocio.

---

# 8. Subcapacidades Candidatas

## 8.1 Cobranca Manual

Responsavel por organizar e registrar recuperacao operacional de credito.

Capability materializada: `PRODUCT-005 - Administrar Cobrancas`.

Modelo candidato:

- Aggregate: `CasoCobranca`;
- Entities: `AcaoCobranca`, `PromessaPagamento`, `ApropriacaoPagamentoPromessa`;
- Value Objects: `StatusCobranca`, `TipoAcaoCobranca`, `DataRetorno`.

## 8.2 Agenda Operacional

Responsavel por compromissos, lembretes e retornos.

Capability materializada: `PRODUCT-006 - Administrar Agenda`.

Modelo candidato:

- Aggregate: `AgendaOperacional`;
- Entities: `CompromissoAgenda`, `Lembrete`;
- Value Objects: `JanelaAgenda`, `PrioridadeAgenda`, `StatusCompromisso`.

## 8.3 Comunicacao Manual

Responsavel por historico de contato com o devedor.

Capability materializada: `PRODUCT-007 - Administrar Comunicacao`.

Modelo candidato:

- Aggregate: `HistoricoComunicacao`;
- Entity: `RegistroComunicacao`;
- Value Objects: `CanalComunicacao`, `ResultadoContato`.

## 8.4 Relatorios Basicos

Responsavel por consultas consolidadas e indicadores operacionais.

Capability materializada: `PRODUCT-008 - Administrar Relatorios`.

Modelo candidato:

- Read Model: `ResumoCarteira`;
- Read Model: `VencimentoOperacional`;
- Read Model: `IndicadorInadimplencia`;
- Read Model: `FluxoCaixaPrevistoRealizado`.

---

# 9. Fluxos Candidatos

## 9.1 Acompanhamento de Vencimento

1. Motor gera ou atualiza parcelas.
2. Na consulta, o Motor materializa a projecao oficial para a `data_referencia`,
   classificando vencimento e inadimplencia sem depender de Scheduler.
3. Operacao Diaria consome a projecao sem repetir a regra temporal.
4. Agenda exibe vencimentos financeiros por periodo, separados de itens
   operacionais criados pelo usuario.
5. Usuario cria compromisso ou lembrete.
6. Compromisso ou lembrete aberto pode ser concluido, cancelado ou reagendado.

## 9.2 Cobranca Manual

1. Parcela vencida ou operacao com atraso aparece na fila operacional.
2. Usuario registra acao de cobranca.
3. Usuario registra resultado do contato.
4. Opcionalmente registra promessa de pagamento.
5. Pagamento futuro e confirmado apenas pelo Motor Financeiro.
6. Informacao manual de pagamento usa estado `pagamento_informado`.
7. A aplicacao valida Pagamentos oficiais processados ou confirmados e nao
   estornados, sempre do mesmo Tenant, Carteira e Emprestimo.
8. Somente valores recebidos entre o registro da promessa e o fim da data
   prometida contribuem; a soma deve alcancar o valor declarado.
9. Quando houver Parcela referenciada, apenas valores oficialmente alocados a
   essa Parcela contribuem para o cumprimento.
10. Cada fracao monetaria apropriada fica indisponivel para outras promessas; o
    rateio e permitido, mas a soma apropriada nao excede o valor elegivel do
    Pagamento.
11. Estorno invalida as apropriacoes correspondentes e reavalia as promessas
    afetadas: soma insuficiente retorna a promessa a `pendente` antes do limite
    prometido ou a `descumprida` depois dele.
12. `PromessaPagamentoCumprimentoInvalidado` somente e emitido quando a promessa
    estava `cumprida` e passa a `pendente` ou `descumprida`; se continuar
    `cumprida`, apenas a trilha da reavaliacao e preservada.
13. No MVP, `ApropriarPagamentoPromessa` associa explicitamente um Pagamento
    elegivel. `ReavaliarPromessaPagamento` executa sincronicamente depois da
    apropriacao, do consumo de estorno e antes de devolver promessa vencida. A
    mesma `data_referencia` e versao dos fatos produzem o mesmo estado, sem
    descobrir Pagamentos automaticamente nem depender de Scheduler ou batch.

## 9.3 Comunicacao Manual

1. Usuario seleciona devedor ou emprestimo.
2. Sistema registra canal, data, responsavel, resumo e resultado.
3. Historico fica disponivel para Cobranca, Agenda e consulta operacional.
4. Nenhum disparo externo ocorre no MVP.

## 9.4 Relatorios Basicos

1. Sistema consolida fatos de Cadastro, Contratos e Motor.
2. Usuario consulta indicadores por tenant/carteira/periodo.
3. Relatorios exibem dados derivados de fatos oficiais.
4. Leituras pesadas devem evoluir para read models/projections antes de escala.

---

# 10. Decisoes Preliminares

## DA-701 - Operacao Diaria e downstream

Operacao Diaria consome fatos oficiais de contextos anteriores. Ela nao comanda
criacao de emprestimo, liberacao de contrato nem mudanca financeira definitiva.

## DA-702 - Motor permanece como fonte oficial financeira

Qualquer saldo, valor vencido, valor de quitacao, juros, amortizacao ou memoria
de calculo exibido no EPIC-007 deve vir do Motor Financeiro ou de read model
derivado de evento/fato do Motor.

## DA-703 - Comunicacao e manual no MVP

O MVP registra comunicacoes realizadas pelo usuario, mas nao envia mensagens por
provedores externos. Notification e integracoes de canal ficam para ciclo futuro.

## DA-704 - Agenda nasce sem scheduler obrigatorio

Agenda pode iniciar com compromissos e lembretes registrados/consultados pelo
usuario. Rotinas automaticas de scheduler, batch e disparo ficam fora do MVP.

## DA-705 - Relatorios basicos antes de analytics

Relatorios devem iniciar com consultas e read models operacionais suficientes
para o MVP. BI avancado, data lake e analytics preditivo ficam fora de escopo.

## DA-706 - Promessa nao altera contrato nem emprestimo

Promessa de pagamento e fato operacional. Ela nao altera plano de parcelas,
saldo, juros, vencimento financeiro ou condicoes de renegociacao.

## DA-707 - Cobranca e o contexto primario do EPIC-007

O EPIC-007 e transversal conforme ROADMAP-ALIGNMENT, mas adota Cobranca como
contexto primario. Agenda, Comunicacao e Relatorios sao contextos secundarios
com Capabilities proprias e integracao conformista/ACL.

## DA-708 - Relatorios basicos entram no mesmo ciclo

O MVP inclui resumo da Carteira, vencimentos e inadimplencia, pagamentos e
operacoes encerradas, alem de fluxo previsto e realizado.

## DA-709 - Valor de promessa e declaratorio

Promessa registra data e valor positivo livre informado pelo devedor. A
referencia primaria e Emprestimo; Parcela e opcional. O valor declarado nao
substitui saldo, parcela ou valor de quitacao oficial do Motor.

## DA-710 - Referencias operacionais atravessam contratos

Acao de Cobranca pertence ao Emprestimo e pode referenciar Parcela. Devedor e
derivado do Emprestimo. Agenda e Comunicacao podem referenciar Cobranca apenas
por identificadores e contratos/ACL, sem dependencia de modelo interno.
Toda referencia fornecida deve resolver para a mesma cadeia Tenant, Carteira,
Devedor e Emprestimo. A ACL devolve os identificadores canonicos; a aplicacao
nao confia em IDs redundantes recebidos no payload.

## DA-711 - API estruturada antes de exportacoes

O MVP entrega respostas API estruturadas. Exportacao CSV/PDF fica fora do
EPIC-007.

## DA-712 - Read models sincronizados e reconstruiveis no MVP

Read models iniciais serao atualizados sincronicamente no mesmo PostgreSQL e
deverao suportar rebuild a partir das fontes oficiais. Event Bus e projecao
assincrona permanecem evolucoes futuras.

## DA-713 - Cumprimento exige Pagamento elegivel

Uma promessa somente fica cumprida quando a soma de um ou mais Pagamentos
oficiais, processados ou confirmados e nao estornados, alcanca o valor declarado
entre o registro da promessa e o fim da data prometida. Todos os Pagamentos
devem pertencer ao mesmo Tenant, Carteira e Emprestimo. Quando a promessa
referencia Parcela, somente alocacoes oficiais nessa Parcela sao elegiveis.
Pagamento insuficiente, posterior, estornado ou de outra operacao nao cumpre a
promessa e nao altera fatos financeiros.

## DA-714 - Consulta nao produz evento de negocio

Consultas de Relatorios nao produzem evento de dominio nem trilha em
`audit_log`, conforme ADR-002. Observabilidade tecnica pode registrar metricas e
logs nao persistidos como auditoria de negocio, sem alterar estado.

## DA-715 - Apropriacao de Pagamento e exclusiva e rastreavel

O cumprimento usa apropriacoes monetarias explicitas entre Pagamento e promessa.
Um Pagamento pode ser rateado, mas cada fracao de seu valor elegivel e apropriada
uma unica vez e a soma das apropriacoes ativas nunca supera o valor recebido. A
apropriacao preserva Pagamento, promessa, valor, Tenant, Carteira, Emprestimo e,
quando aplicavel, Parcela. A reserva do valor e atomica; concorrencia que tente
reutilizar a mesma disponibilidade e recusada com `409`.

## DA-716 - Estorno reavalia promessas afetadas

O estorno invalida todas as apropriacoes daquele Pagamento e recalcula o estado
operacional das promessas afetadas. Se outras apropriacoes ainda atingirem o
valor declarado, a promessa permanece cumprida. Caso contrario, volta a
`pendente` ate o fim da data prometida ou passa a `descumprida` depois desse
limite. Quando houver perda do estado `cumprida`, a mudanca emite
`PromessaPagamentoCumprimentoInvalidado`, preserva motivo e referencia ao
estorno e nao altera fatos financeiros do Motor.

O evento somente e emitido uma vez quando o estado anterior era `cumprida` e o
novo estado e `pendente` ou `descumprida`. Promessa que permanece `cumprida` ou
que nunca esteve cumprida nao emite invalidacao. O payload preserva
`promessa_id`, `pagamento_id`, `estorno_id`, estados anterior/novo, motivo,
instante, autoria sistemica, Tenant, Carteira, versao e chave idempotente.

## DA-717 - Vencimento e inadimplencia sao projecoes oficiais do Motor

O Motor e o produtor de `SituacaoParcelaNaDataV1`. Para uma `data_referencia`
explicita, sua consulta/projecao sincrona devolve estado oficial, classificacao
`futura`, `vencida`, `regularizada` ou `cancelada`, datas, valores oficiais e
`regularizada_em`. O Motor pode materializar a situacao durante a consulta, sem
Scheduler, e deve produzir o mesmo resultado para a mesma versao dos fatos e
data. Cobranca, Agenda e Relatorios apenas filtram, ordenam, agrupam e exibem a
projecao.

## DA-718 - Estados da PromessaPagamento

| Estado atual | Gatilho | Proximo estado | Origem e guarda |
|---|---|---|---|
| criacao | registro valido | `pendente` | operador; data futura e valor positivo |
| `pendente` | informacao manual | `pagamento_informado` | operador; antes do fim da data; nao confirma Pagamento |
| `pendente` ou `pagamento_informado` | apropriacoes elegiveis atingem o valor | `cumprida` | sistema; Pagamentos oficiais dentro da janela |
| `pendente` ou `pagamento_informado` | fim da data sem valor suficiente | `descumprida` | sistema ou operador; justificativa obrigatoria quando manual |
| `descumprida` | Pagamento oficial retroativo recebido dentro da janela | `cumprida` | sistema; preserva a correcao historica |
| `cumprida` | estorno reduz a soma antes do limite | `pendente` | sistema; emite invalidacao |
| `cumprida` | estorno reduz a soma depois do limite | `descumprida` | sistema; emite invalidacao |
| `cumprida` | estorno mantem soma suficiente | `cumprida` | sistema; nao emite invalidacao |

As transicoes sistemicas sao materializadas de forma lazy e deterministica.
`ApropriarPagamentoPromessa` cria a apropriacao explicita; depois dela, do
consumo de `PagamentoEstornadoV1` e antes de devolver uma promessa vencida,
`ReavaliarPromessaPagamento` materializa no maximo uma transicao da tabela por
promessa afetada, na mesma Unit of Work, e usa `data_referencia` explicita.
Descoberta ou pareamento automatico de Pagamentos, batch e Scheduler permanecem
fora do MVP.

Repetir o mesmo comando ou fato preserva estado e historico sem duplicacao.
Transicao fora da tabela retorna `409`. `cumprida` e `descumprida` nao sao
terminais diante de reconhecimento ou estorno posterior de fato financeiro cuja
data oficial esteja dentro da janela prometida.

## DA-719 - Integridade referencial e erros protegidos

Acao e promessa recebem `emprestimo_id`; `devedor_id` e derivado e
`parcela_id`, quando informado, deve pertencer ao Emprestimo. Agenda e
Comunicacao validam por contrato/ACL a cadeia de toda referencia opcional. Todos
os recursos devem pertencer ao mesmo Tenant e Carteira do Principal.

Formato, payload, enum, data ou identificador malformado retorna `400`. Recurso
de ID valido inexistente ou inacessivel, inclusive cross-tenant, retorna `404`
logico. Transicao proibida, cadeia visivel incompatível, chave idempotente com
payload diferente, versao obsoleta ou conflito concorrente retorna `409`.
Replay da mesma chave com o mesmo payload devolve o resultado original.

## DA-720 - Agregacao operacional nao e calculo financeiro

Relatorios podem executar `count`, `sum` e `group` sobre campos oficiais e
comparar datas/estados oficiais para filtro e apresentacao. Tambem e permitida a
soma de apropriacoes oficiais para verificar cumprimento de promessa.
Permanecem proibidos fora do Motor: juros, mora, multa, amortizacao, saldo,
quitacao, arredondamento monetario, memoria de calculo ou derivacao que substitua
um valor financeiro oficial. Fluxo realizado soma
`valor_efeito_realizado_assinado`, fornecido pelo Motor, sem reconstruir a regra
de compensacao do estorno.

---

# 11. Contratos de Integracao

## 11.1 Motor Financeiro -> Operacao Diaria

Contrato minimo esperado:

- `schema_version`, `evento_ou_projecao_id` e `source_version`;
- `tenant_id`;
- `carteira_id`;
- `devedor_id`;
- `contrato_id` quando aplicavel;
- `emprestimo_id`;
- `pagamento_id`, `estorno_id` e chave idempotente quando aplicavel;
- `parcela_id` ou apropriacoes `[{parcela_id, valor_apropriado}]` quando aplicavel;
- estado anterior e atual da operacao, Parcela ou Pagamento;
- datas de vencimento, pagamento, estorno e `data_referencia`;
- classificacao oficial `futura|vencida|regularizada|cancelada` e
  `regularizada_em` quando aplicavel;
- valores oficiais ja calculados pelo Motor;
- `valor_efeito_realizado_assinado` para registro ou estorno de Pagamento;
- motivo e autoria do estorno quando aplicavel;
- `ocorrido_em`, `registrado_em` e versao do fato/projecao.

O produtor de `PagamentoEstornadoV1` e um service do Motor que, na mesma Unit
of Work, reverte efeitos financeiros, persiste o estado e disponibiliza o fato
idempotente. Cobranca e Relatorios consomem as apropriacoes revertidas e o
efeito realizado assinado; nao reconstroem a reversao.

## 11.2 Cadastro -> Operacao Diaria

Contrato minimo esperado:

- `tenant_id`;
- `carteira_id`;
- `devedor_id`;
- nome ou identificador exibivel;
- contatos cadastrados;
- situacao cadastral;
- versao ou timestamp do cadastro.

## 11.3 Operacao Diaria -> Relatorios

Contrato minimo esperado:

- fatos de cobranca;
- compromissos e lembretes;
- historico de comunicacao;
- referencias para emprestimo/devedor/carteira;
- responsavel pela acao;
- periodo de competencia.

## 11.4 Contratos -> Relatorios

Contrato minimo `EncerramentoOperacaoV1`:

- `schema_version`, `evento_ou_projecao_id` e `source_version`;
- `source_context`;
- `tenant_id`, `carteira_id` e `devedor_id`;
- `contrato_id` e `emprestimo_id` quando existente;
- estado anterior e estado atual;
- `tipo_encerramento`: `quitacao_financeira`, `renegociacao_financeira`,
  `encerramento_administrativo` ou `cancelamento_contratual`;
- data efetiva, motivo, autoria e chave idempotente;
- `ocorrido_em` e `registrado_em`.

Quitacao e renegociacao originam-se no Motor. Encerramento administrativo e
cancelamento originam-se em Contratos e nao podem ser inferidos a partir do
estado financeiro do Emprestimo.

---

# 12. Riscos

| Risco | Impacto | Mitigacao |
|---|---|---|
| Recalculo financeiro em Cobranca ou Relatorios | divergencia de saldo e quebra do Core Domain | guardrail anti-calculo fora do Motor e testes AST. |
| Promessa tratada como renegociacao | contrato/emprestimo alterado sem regra financeira oficial | modelar promessa como fato operacional sem efeito financeiro. |
| Agenda depender de scheduler prematuro | atraso por infraestrutura futura | iniciar com agenda manual e consultas por periodo. |
| Comunicacao virar envio externo no MVP | dependencia de provedores e risco LGPD | registrar historico manual; externalizacao futura por Notification. |
| Relatorios pesados no banco transacional | degradacao de performance | limitar escopo e preparar read models/projections. |
| Inadimplencia calculada por regra paralela | resultado inconsistente com Motor | consumir estado oficial ou projecao do Motor. |
| Falta de auditoria de acoes | impossibilidade de rastrear cobranca | registrar usuario, data, tenant, carteira e origem da acao. |
| Vazamento cross-tenant | exposicao de dados sensiveis | aplicar tenant/carteira em queries, fixtures e testes negativos. |

---

# 13. Plano Inicial de Testes

## 13.1 Dominio

- criar CasoCobranca a partir de emprestimo/parcela referenciada;
- registrar acao de cobranca com responsavel e resultado;
- registrar promessa de pagamento sem alterar saldo;
- impedir promessa com data/valor invalidos;
- impedir cumprimento com Pagamento de outro escopo ou Emprestimo, insuficiente,
  posterior, estornado ou sem alocacao na Parcela referenciada;
- impedir que apropriacoes entre promessas excedam o valor elegivel do Pagamento;
- permitir rateio do Pagamento sem dupla apropriacao da mesma fracao monetaria;
- impedir dupla apropriacao sob comandos concorrentes;
- invalidar apropriacoes apos estorno e reavaliar promessa para `pendente`,
  `descumprida` ou ainda `cumprida`, conforme data e soma remanescente;
- emitir invalidacao somente quando uma promessa `cumprida` perder esse estado;
- cobrir todas as transicoes da tabela DA-718, inclusive correcao retroativa;
- cobrir reavaliacao por consulta, comando e fato com a mesma `data_referencia`;
- criar compromisso ou lembrete de Agenda e transicionar estados validos;
- rejeitar referencias de cadeias, Tenant ou Carteira incompatíveis;
- registrar comunicacao manual com canal e resultado obrigatorios.

## 13.2 Guardrails

- falhar se Cobranca, Agenda, Comunicacao ou Relatorios usarem `float`;
- falhar se contextos do EPIC-007 calcularem juros, saldo, amortizacao,
  quitacao ou memoria de calculo;
- falhar se promessa de pagamento alterar Emprestimo, Parcela ou Contrato;
- falhar se relatorio recomputar formula financeira em vez de consumir fato;
- permitir `count`, `sum`, `group`, filtros e comparacoes sobre fatos oficiais;
- falhar diante de juros, mora, multa, amortizacao, saldo, quitacao,
  arredondamento ou memoria de calculo fora do Motor.

## 13.3 Aplicacao

- services devem exigir principal autenticado;
- commands de escrita devem ser idempotentes quando expostos por API;
- consultas devem respeitar tenant/carteira;
- consultas de vencimento devem exigir `data_referencia` e consumir
  `SituacaoParcelaNaDataV1`;
- relatorios devem filtrar por periodo e escopo autorizado;
- pagamentos devem exibir bruto, estornos e liquido separadamente, somando
  somente `valor_efeito_realizado_assinado` no fluxo realizado;
- encerramento administrativo deve ser consumido do contrato 11.4;
- consultas de Relatorios nao devem produzir evento de dominio nem `audit_log`.

## 13.4 Persistencia

- migrations para Cobranca, Agenda, Comunicacao e read models basicos;
- constraints de tenant/carteira e chaves naturais/idempotentes;
- invariante transacional que bloqueie dupla apropriacao e garanta que a soma
  ativa nao exceda o valor elegivel do Pagamento;
- repositories isolados por contexto;
- testes de downgrade/upgrade de migrations.

## 13.5 API/RBAC/OpenAPI

- endpoints protegidos por permissoes especificas do EPIC-007;
- respostas `400/401/403/404/409` documentadas conforme DA-719;
- testes de cross-tenant;
- testes de referencia malformada, inexistente e de cadeia incompatível;
- testes de usuario sem permissao;
- testes de contrato OpenAPI para rotas novas.

---

# 14. Decisoes de Product Fechadas

- relatorios do ciclo: resumo da Carteira, vencimentos/inadimplencia,
  pagamentos/encerramentos e fluxo previsto/realizado;
- promessa: data e valor positivo declaratorio, com Emprestimo obrigatorio e
  Parcela opcional;
- acao de Cobranca: Emprestimo como referencia primaria e Devedor derivado;
- Agenda e Capability/contexto independente, integrada por contrato/ACL;
- entrega de relatorios por API estruturada, sem CSV/PDF no MVP;
- read models sincronizados no mesmo PostgreSQL e reconstruiveis no MVP;
- cumprimento de promessa exige Pagamentos elegiveis conforme DA-713;
- cumprimento usa apropriacao exclusiva conforme DA-715 e e reavaliado apos
  estorno conforme DA-716;
- vencimento/inadimplencia sao consumidos conforme DA-717;
- estados de promessa seguem a tabela DA-718;
- referencias e erros protegidos seguem DA-719;
- agregacoes permitidas e formulas proibidas seguem DA-720;
- consultas de Relatorios nao geram evento de dominio nem auditoria de negocio.

---

# 15. Resultado do Discovery

O EPIC-007 pode avancar para plano tecnico com
uma premissa central: Operacao Diaria organiza e registra o trabalho diario do
credor, mas todos os fatos financeiros definitivos continuam pertencendo ao
Motor Financeiro.

O PLAN deve tratar como dependencias bloqueantes, antes dos consumidores do
EPIC-007: o Motor produzir `SituacaoParcelaNaDataV1`, `PagamentoEstornadoV1` e
`valor_efeito_realizado_assinado`; e Contratos disponibilizar
`EncerramentoOperacaoV1`. Estes contratos ainda nao existem no backend e nao
podem ser simulados ou recalculados pela Operacao Diaria.

Proximo passo limpo:

1. criar o plano tecnico de implementacao com backlog de IMPs;
2. iniciar suites de dominio antes do codigo.

---

# 16. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.6.0 | 2026-08-10 | Transicao por promessa e dependencias bloqueantes dos produtores upstream explicitadas. |
| 1.5.0 | 2026-08-10 | Gatilhos sincronicos da promessa sem Scheduler e propagacao completa do contrato HTTP formalizados. |
| 1.4.0 | 2026-08-10 | Vencimento oficial, estorno, encerramento administrativo, estados de promessa, integridade referencial e guardrails formalizados. |
| 1.3.0 | 2026-08-10 | Apropriacao exclusiva de Pagamentos e reavaliacao apos estorno formalizadas. |
| 1.2.0 | 2026-08-10 | Elegibilidade de Pagamentos e semantica de consultas sem evento/auditoria formalizadas apos recertificacao. |
| 1.1.0 | 2026-08-10 | Decisoes de Product fechadas, quatro Capabilities materializadas, Cobranca definida como contexto primario e semantica de promessa corrigida. |
| 1.0.0 | 2026-08-10 | Discovery/SDD inicial do EPIC-007 - Operacao Diaria. |
