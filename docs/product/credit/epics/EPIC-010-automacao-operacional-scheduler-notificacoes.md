# EPIC-010 - Automacao Operacional, Scheduler e Notificacoes

**ID:** EPIC-010

**Versão:** 1.1.0

**Status:** Proposto

---

# 1. Objetivo

Automatizar lembretes operacionais por jobs duraveis e enviar notificacoes
transacionais governadas, sem mover regras de Agenda, Comunicacao ou Motor para
os componentes tecnicos Scheduler e Notification.

O Epic atravessa `PRODUCT-006 - Administrar Agenda` e
`PRODUCT-007 - Administrar Comunicacao`. Nao cria uma Capability nova porque a automacao e um
habilitador tecnico dessas capacidades, nao uma funcao de produto independente.

---

# 2. Valor de Negócio

Reduz trabalho manual e perda de prazos, preservando rastreabilidade,
isolamento por Tenant/Carteira e controle sobre cada efeito externo.

---

# 3. Escopo

- persistir, reivindicar, executar, recuperar e cancelar jobs duraveis;
- criar e cancelar o job do Lembrete na mesma transacao e UnitOfWork;
- revalidar a origem antes de qualquer efeito;
- enviar e-mail transacional no primeiro incremento por porta de canal;
- aplicar consentimento, opt-out e templates aprovados e versionados;
- distinguir aceite, falha temporaria, permanente e resultado desconhecido;
- impedir reenvio automatico quando o resultado externo for desconhecido;
- registrar Comunicacao uma unica vez depois de aceite confirmado;
- disponibilizar operacao administrativa protegida e health interno do worker;
- preservar correlation ID, auditoria e mascaramento de dados.

Decisões de Produto:

- nenhuma nova Capability sera emitida; o Epic permanece sob
  PRODUCT-006/PRODUCT-007;
- e-mail transacional e o unico canal do primeiro incremento;
- somente contato de e-mail ativo, autorizado, do mesmo Tenant/Carteira e sem
  opt-out pode receber notificacao;
- a allowlist inicial contem somente `lembrete_operacional_v1`, com parametros
  `data_hora` e `canal_atendimento`; nova finalidade exige nova versao ou novo
  template e aprovacao de responsavel autorizado antes de ativacao;
- o contrato de envio confirma aceite do provedor, nao entrega ou leitura;
- `POST /credit/agenda/lembretes/{lembrete_id}/enviar` deixa de representar
  envio manual e fica restrito a conciliacao administrativa auditada; o fluxo
  normal somente transiciona para `enviado` apos aceite do canal pelo worker;
- ADR-009 fecha o provedor Resend, o ambiente de teste verificavel e o contrato
  do canal; ADR-007 fecha lag, tentativas, backoff e retencao; ambas estao
  aceitas e antecedem o PLAN tecnico.

---

# 4. Fora do Escopo

- WhatsApp, SMS, push, campanhas ou marketing em massa;
- entrega exatamente uma vez, leitura ou entrega final sem receipt confiavel;
- broker externo, outbox generica, workflow complexo ou integracao bancaria;
- frontend, cloud/IaC ou dashboards APM externos;
- qualquer calculo ou alteracao de fato financeiro.

---

# 5. Features

- FEATURE-042 - Automatizar Lembretes Operacionais;
- FEATURE-043 - Processar Jobs Duraveis;
- FEATURE-044 - Enviar Notificacoes Transacionais;
- FEATURE-045 - Operar e Reconciliar Automacao.

---

# 6. Dependências

- PRODUCT-006 - Administrar Agenda;
- PRODUCT-007 - Administrar Comunicacao;
- EPIC-007 - Operacao Diaria;
- EPIC-006 - IAM;
- EPIC-008 - Fundacao Operacional e Observabilidade;
- EPIC-002 - Cadastro de Devedores;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- ADR-007 - Scheduler / Batch Processing, obrigatoria antes do PLAN;
- ADR-009 - Notifications / Channels, obrigatoria antes do PLAN;
- [Discovery/SDD do EPIC-010](../../../audits/discoveries/EPIC-010-automacao-operacional-scheduler-notificacoes-discovery.md).

---

# 7. Critérios de Aprovação

- Product, Features e User Stories permanecem consistentes com o Discovery;
- ADR-007 aceita fecha lag, tentativas, backoff e retencao antes do PLAN;
- ADR-009 aceita fecha provedor e ambiente de teste verificavel antes do PLAN;
- Lembrete e job sao criados ou cancelados atomicamente;
- nenhum job produz efeito sem revalidar a origem;
- lease impede conclusao concorrente ou tardia;
- falha permanente exige solicitacao corrigida e versionada;
- resultado desconhecido bloqueia reenvio ate conciliacao;
- dados pessoais, payload integral e segredos nao vazam em logs ou APIs;
- operacoes administrativas respeitam IAM, Tenant e Carteira;
- Scheduler e Notification nao calculam nem reinterpretam fatos financeiros.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.1.0 | 2026-08-11 | ADR-007 e ADR-009 aceitas; escolhas tecnicas encerradas antes do PLAN. |
| 1.0.0 | 2026-08-11 | Primeira versao formal do EPIC-010. |
