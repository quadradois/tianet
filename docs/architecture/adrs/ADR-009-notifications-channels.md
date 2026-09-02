# ADR-009: Notifications e Channels

> **Status:** Aceito
> **Data:** 2026-08-11
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura, Produto e Seguranca
> **Aprovacao:** Arquitetura / 2026-08-11
> **Substitui:** —
> **Substituido por:** —

---

## Contexto

O EPIC-010 introduz e-mail transacional para lembretes operacionais. A fronteira
precisa separar intencao de negocio, execucao tecnica e evidencia externa. A
marcacao local de um Lembrete como enviado nao comprova que um provedor aceitou
a mensagem, e uma falha depois da transmissao pode tornar o resultado incerto.

Notification nao substitui o historico de Comunicacao, nao decide elegibilidade
do Lembrete e nao interpreta fatos financeiros.

---

## Decisao

### Canal, provedor e porta

E-mail transacional e o unico canal inicial. O adaptador concreto usa a API
HTTPS do Resend, `POST /emails`, por `httpx`, atras da porta
`NotificationChannel`. Nao sera introduzido SDK do provedor.

A porta recebe uma solicitacao ja validada e renderizada e devolve resultado
tipado. Ela nao abre transacao de dominio nem altera Lembrete ou Comunicacao.
Timeouts do adaptador sao 3 segundos para conexao e 10 segundos para leitura e
escrita. O adaptador nao faz retry interno; o Scheduler governa tentativas.

A chave Resend tem apenas `sending_access`, fica restrita ao dominio de envio
quando suportado e vive em variavel de ambiente ou secret manager. Chave,
cabecalho de autorizacao e corpo integral nunca sao persistidos ou logados.

### Ambiente verificavel

O Resend nao oferece um modo sandbox isolado. Desenvolvimento integrado usa
projeto e API key de teste separados da producao e somente os enderecos de teste
`resend.dev` documentados pelo provedor. CI e testes locais usam um fake
deterministico sem credencial nem rede. O teste opt-in contra o projeto de teste
nao e gate obrigatorio de pull request.

Producao usa projeto, chave, dominio e remetente verificado exclusivos. Nenhuma
credencial de teste pode iniciar em producao, e vice-versa.

### Identidade idempotente e resultado

Cada notificacao possui `notification_id`, versao de solicitacao, hash do
payload canonico e chave idempotente estavel. A chave enviada ao provedor e
`notification/<sha256>` derivada de Tenant, origem, versao, finalidade e versao
do template; nao contem e-mail, nome, documento ou outra PII.

A chave e o hash sao persistidos antes do efeito externo. Reuso da chave com
payload diferente e conflito permanente. Como o provedor conserva idempotencia
por 24 horas, o ciclo automatico de retry deve terminar nessa janela. Se nao for
possivel provar que uma requisicao anterior nao foi aceita, inclusive timeout
ou reset depois do envio de bytes, o estado e `resultado_desconhecido` e nenhum
reenvio automatico e permitido.

Estados externos normalizados:

| Estado | Evidencia | Acao |
|---|---|---|
| `aceita` | resposta de sucesso com `provider_message_id` | registrar aceite e Comunicacao uma vez |
| `falha_temporaria` | 429, conflito concorrente da mesma chave ou falha comprovadamente anterior ao envio de bytes | retry governado pela ADR-007 |
| `falha_permanente` | 400/422, contato/template invalido, 401/403 ou conflito de payload | corrigir e criar solicitacao versionada |
| `resultado_desconhecido` | 5xx, 2xx malformado, timeout/reset apos transmitir bytes ou qualquer resposta sem prova de nao aceite | bloquear retry e conciliar |

Um `409` por processamento concorrente da mesma chave e temporario; um `409`
por mesma chave com payload diferente e permanente. `Retry-After` segue os
limites da ADR-007. Retry somente ocorre quando ha prova de que o provedor nao
aceitou o efeito ou quando a mesma chave ainda esta protegida pela janela
idempotente. Na duvida, prevalece `resultado_desconhecido`. Aceite significa
apenas que o provedor aceitou a requisicao; nao promete entrega, leitura ou acao
do destinatario.

### Consentimento e contato autorizado

Notification mantem `PreferenciaNotificacao` por Tenant, Carteira, Devedor,
Contato e canal, com evidencia de consentimento, origem, estado permitido ou
opt-out, instante e ator. Ausencia, ambiguidade ou opt-out implica bloqueio por
padrao. O Contato continua sendo a fonte do endereco e nao e duplicado; contato
removido ou fora do Tenant/Carteira e inelegivel.

Mudanca de preferencia impede novas solicitacoes, mas nao apaga historico. Cada
tentativa registra somente identificadores, hashes e metadados mascarados
necessarios para auditoria tecnica.

### Templates

Templates sao persistidos e versionados no PostgreSQL. Uma versao ativada e
imutavel e contem codigo, versao, canal, status, assunto, corpo, allowlist de
parametros, hash, autor, aprovador, motivo e timestamps.

O primeiro incremento aceita apenas `lembrete_operacional_v1`, com
`data_hora` e `canal_atendimento`:

- `data_hora` e armazenado em UTC e renderizado na timezone IANA do Tenant com
  offset explicito;
- `canal_atendimento` e um rotulo ou URL institucional aprovado, nunca contato
  pessoal livre;
- mensagem livre, HTML arbitrario e parametros extras sao rejeitados;
- nova finalidade exige nova versao ou template e aprovacao autorizada.

### Historico e conciliacao

Notification registra intencao e tentativas. Depois do aceite externo, uma
unica UnitOfWork marca a notificacao como aceita, transiciona o Lembrete para
enviado, cria uma unica Comunicacao ligada por `notification_id` e conclui o
job. Constraints unicas tornam esse replay idempotente. Se a transacao local
falhar, o worker repete a consulta ou requisicao com a mesma chave dentro da
janela do provedor e reaplica a UnitOfWork; fora da janela, sem prova externa,
marca `resultado_desconhecido` e exige conciliacao.

A Comunicacao registra ator tecnico, template/versao, canal, instante e
`provider_message_id` protegido. O registro nao afirma entrega ou leitura e nao
substitui o historico manual.

O endpoint legado
`POST /credit/agenda/lembretes/{lembrete_id}/enviar` torna-se alias depreciado
de conciliacao e jamais chama o provedor. Ele so aceita notificacao em
`resultado_desconhecido`, exige permissao `notificacao.conciliar`,
`Idempotency-Key`, `notification_id`, evidencia externa, motivo e auditoria.
Antes da alteracao, o sistema prova que a notificacao referencia o mesmo
`lembrete_id`, tentativa, Tenant e Carteira da rota e do Principal.

A unica evidencia capaz de mudar o estado e um `provider_message_id` e status
consultados pelo adaptador com credencial restrita, acompanhados do instante
observado e da identidade idempotente correspondente. Declaracao humana, texto
livre, print ou identificador nao verificavel pode complementar a auditoria, mas
nao comprova nao aceite, nao muda o resultado desconhecido e jamais libera
reenvio. Sem evidencia verificavel do provedor, a notificacao permanece
`resultado_desconhecido`. A conciliacao aplica a mesma UnitOfWork atomica do
fluxo normal. Repeticao identica e idempotente; evidencia divergente responde
conflito.

Nao existe endpoint de disparo arbitrario. Permissoes iniciais distintas sao
`automacao.job.consultar`, `automacao.job.cancelar`, `automacao.job.retry`,
`notificacao.consultar`, `notificacao.conciliar` e
`notificacao.template.gerir`, sempre com Tenant/Carteira.

Webhooks, receipts de entrega/leitura, novos canais, campanhas e marketing
ficam fora do primeiro incremento. Uma revisao futura pode adicionar conciliacao
automatica sem alterar o significado de aceite desta ADR.

### Seguranca e guardrails

- Logs nao contem destinatario integral, assunto/corpo, PII, token ou segredo.
- APIs administrativas devolvem apenas dados mascarados e necessarios.
- Correlation ID, job ID e notification ID atravessam a cadeia.
- Scheduler e Notification nao calculam, corrigem ou reinterpretam fatos
  financeiros.
- Nenhum canal altera diretamente o agregado de origem.

---

## Alternativas Consideradas

| Opcao | Pros | Contras | Decisao |
|---|---|---|---|
| SMTP direto | amplo suporte | menor contrato de idempotencia e status | rejeitada |
| Resend por SDK | integracao rapida | dependencia adicional desnecessaria | rejeitada |
| Resend REST por porta | idempotencia documentada e baixo acoplamento | dependencia externa e janela de 24h | escolhida |
| Multiplos canais iniciais | maior alcance | amplia consentimento e operacao cedo demais | rejeitada |

---

## Consequencias

- Persistencia deve modelar preferencia, template, notificacao e tentativa.
- A semantica atual de `enviar` precisa ser migrada para conciliacao auditada.
- Falhas incertas podem exigir operacao humana e nao podem ser ocultadas por
  retry cego.
- Fake deterministico e testes de contrato protegem CI; teste real e opt-in.
- Trocar de provedor exige novo adaptador e revisao da estrategia idempotente,
  nao mudanca nos contextos de origem.

---

## Validacao

- testes de contrato da porta classificam sucesso, 4xx, 409, 429, 5xx e timeout;
- mesma identidade/payload nao duplica efeito; payload divergente conflita;
- resultado desconhecido bloqueia retry e exige conciliacao;
- opt-out, contato removido e escopo divergente bloqueiam antes de renderizar;
- template rejeita mensagem livre e parametros fora da allowlist;
- Comunicacao e registrada uma vez, apenas apos aceite;
- logs e respostas nao vazam PII ou segredos;
- endpoint legado nao chama provedor nem permite disparo arbitrario.

---

## Referencias

- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes;
- AMP-001 - reserva arquitetural ADR-009;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- ADR-015 - CI/CD e Gates de Qualidade;
- ADR-016 - Observability, Logging e Correlation ID;
- FOUNDATION-007 - Product Map;
- FOUNDATION-009 - Capability Map;
- [Resend - Send Email](https://resend.com/docs/api-reference/emails/send-email);
- [Resend - Idempotency Keys](https://resend.com/docs/dashboard/emails/idempotency-keys);
- [Resend - Send Test Emails](https://resend.com/docs/dashboard/emails/send-test-emails);
- [Resend - API Keys](https://resend.com/docs/dashboard/api-keys/introduction).

---

## Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-11 | Decisao do canal, provedor, idempotencia, consentimento, templates e conciliacao. |

---

## Adendo 2026-08-27 — WhatsApp como canal e o ingress do agente

**Autoridade do adendo:** Arquitetura, via PLAN-033/IMP-358. O adendo registra
evolucao; **nada acima foi reescrito** — a decisao historica de e-mail como
unico canal inicial permanece como registro de 2026-08-11.

**WhatsApp entrou como canal de envio.** O IMP-346 (PLAN-032) implementou
`EvolutionWhatsAppNotificationChannel` atras da **mesma porta**
`NotificationChannel`, ao lado do Resend, preservando todas as regras desta ADR:
a porta nao decide elegibilidade, nao faz retry interno (o Scheduler governa
tentativas), nao abre transacao de dominio, e o segredo (`EVOLUTION_INSTANCE_TOKEN`)
vive em variavel de ambiente, nunca em log ou banco. O comprovante de
lancamento e o aviso de sobra ja saem por esse canal.

**E-mail saiu do escopo do MVP** em 2026-08-25 (`contexto-externo.md` §2.3):
nao ha conta Resend. O adaptador continua no codigo; em producao sem credencial,
o canal recusa com `canal_nao_configurado:email` em vez de fingir entrega.

**Recepcao de mensagens nao pertence a esta ADR.** O webhook de entrada do
WhatsApp e do **servico do agente** (PLAN-033/IMP-356), um processo separado com
inbox propria — a API TiaNet continua sem webhook publico. Receipts de
entrega/leitura e conciliacao automatica continuam fora, como o texto original
decidiu; o resultado `DESCONHECIDO` do Evolution segue terminal ate que um
desenho de receipt seja aprovado.


---

## Adendo 2026-09-01 — o token da instancia passa a viver cifrado no banco

**Autoridade do adendo:** Arquitetura, via
[DR-006](../../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md),
resolvida pelo fundador em 2026-08-31, e materializada pelo
[PLAN-034](../../implementation/plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md).
Como no adendo anterior, **nada acima foi reescrito**.

O adendo de 2026-08-27 registra que o `EVOLUTION_INSTANCE_TOKEN` "vive em
variavel de ambiente, nunca em log ou banco". A parte de **log continua valendo,
e sem excecao**. A parte de **banco mudou**, e o motivo e ergonomia operacional,
nao conveniencia.

**Por que mudou.** Quem opera a TiaNet nao tem conta no servidor Evolution, e a
DR-006 decidiu trazer a criacao da instancia para dentro da plataforma. Ao criar,
**a plataforma gera o token** — o Evolution apenas o ecoa. Sem persistir, esse
valor existiria so na requisicao que o criou, e alguem teria de copia-lo para o
`.env` a mao: exatamente o atrito que a tela vem eliminar.

Reconectar uma instancia que ja existe e outra coisa e **nao** exige isso: o
token nao muda no reconnect, e a variavel de ambiente sobrevive a restart. O que
a persistencia resolve e o **nascimento** da instancia, nao a sua reconexao.

**O que muda, exatamente:**

- o **token da instancia** e persistido **cifrado em repouso** (Fernet, chave em
  `WHATSAPP_TOKEN_ENCRYPTION_KEY`, fora do banco). Nunca em texto claro, e a
  recusa e nomeada quando a chave falta — nao ha modo degradado;
- `EVOLUTION_HOST` e as credenciais de **gestao** do tenant continuam em
  variavel de ambiente: nao sao geradas pela plataforma e nao mudam por acao de
  usuario;
- **o ambiente mantem precedencia**, e continua mantendo depois do IMP-370. O
  criterio de pronto daquele item e explicito: com a variavel presente, ela
  prevalece e o comportamento atual nao muda. O repositorio passa a ser a origem
  quando a variavel esta ausente, nao no lugar dela.

  A fase e propria porque trocar a origem do token junto com a criacao da tela
  arriscaria deixar o worker sem canal — e worker sem canal e operacao sem
  aviso.

**O que nao muda.** Nenhuma outra regra desta ADR: a porta continua sem decidir
elegibilidade, sem retry interno e sem abrir transacao de dominio. E o token
continua **fora de log**, de trilha e de metrica.
