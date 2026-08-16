# Contexto Externo

**Versao:** 1.0.0

**Status:** Vivo — mantido manualmente

---

# 1. Para que serve

Este documento registra o que existe **fora do repositorio** e que decisoes
tecnicas dependem: servicos contratados, integracoes de outros projetos,
infraestrutura, e decisoes tomadas em conversa que nunca viraram codigo.

Nenhuma analise de codigo descobre o que esta aqui. Sem este registro, uma
sessao nova conclui corretamente "isto nao existe no repositorio" e propoe
construir algo que a operacao ja tem.

**Regra de leitura:** antes de propor construir qualquer integracao, servico ou
infraestrutura, leia este documento. Se o assunto nao estiver aqui, pergunte
antes de assumir que nao existe.

**Regra de escrita:** quando algo for contratado, integrado ou decidido fora do
codigo, registre aqui na mesma hora. Um item errado e pior que um item ausente.

---

# 2. Integracoes disponiveis

## 2.1 API de WhatsApp

| Campo | Valor |
|---|---|
| Situacao | **Existe e esta em uso em outros projetos do time** |
| Uso previsto na TiaNet | canal oficial de toda comunicacao com o devedor |
| Provedor | *a preencher* |
| Autenticacao | *a preencher* |
| Limites e custo por mensagem | *a preencher* |
| Ambiente de teste | *a preencher* |

Consequencias ja incorporadas ao desenho:

- o envio de comprovante **nao** usa link `wa.me`; vai pela API;
- o adapter entra como implementacao de `NotificationChannel`
  (`src/emprestimo/domain/credit/automacao_ports.py`), ao lado do Resend;
- as conversas com o cliente serao registradas em `RegistroComunicacao`, que ja
  possui `ator_tipo`, `ator_identificador` e `provider_message_id`;
- `CanalComunicacao` ainda **nao** possui o valor `whatsapp` — precisa ser
  acrescentado.

## 2.2 Agente de IA "TiaNet"

Atende pedidos que chegam pelo WhatsApp, registra o pre-cadastro e submete ao
Credor para aprovacao. E o segundo operador do sistema, conforme
`FOUNDATION-001 §3.1`.

| Campo | Valor |
|---|---|
| Situacao | planejado |
| Entra antes ou depois do wizard de emprestimo | *a preencher* |

## 2.3 Resend (e-mail)

`ResendNotificationChannel` existe no codigo e exige `RESEND_API_KEY` e
`RESEND_FROM`. **Nao se sabe se ha conta contratada.** Em `APP_ENV=production` o
worker recusa iniciar sem essas variaveis.

| Campo | Valor |
|---|---|
| Conta contratada | *a preencher* |
| Dominio remetente verificado | *a preencher* |

---

# 3. Infraestrutura

## 3.1 Ambiente local

Documentado em `docs/operations/ambiente-local-docker.md`. Stack completa em
Docker, validada ponta a ponta.

## 3.2 Servidor de producao

| Campo | Valor |
|---|---|
| Situacao | **nao provisionado** |
| Tipo (VPS, cloud gerenciada, PaaS) | *a preencher* |
| Dominio | *a preencher* |
| TLS | *a preencher* |
| Backup do PostgreSQL | *a preencher* |

Nao existe pipeline de CD no repositorio: `.github/workflows/quality.yml` e o
unico workflow e cobre apenas gates de qualidade.

---

# 4. Clientes e tenants

| Nome | Situacao |
|---|---|
| Ivonet | primeiro Tenant previsto; recebera a integracao de WhatsApp |

---

# 5. Ferramentas de apoio

## 5.1 Grafo de conhecimento (graphify)

`graphify-out/` existe no repositorio, porem **gerado em 2026-08-06**: cobre 861
nos, nao inclui os EPIC-003 a EPIC-010 nem o frontend. Deve ser regerado apos
mudancas relevantes de documentacao ou codigo, e consultado antes de afirmar o
que existe.

---

# 6. Perguntas em aberto

Itens que bloqueiam ou distorcem decisoes enquanto nao forem respondidos:

1. Qual provedor de WhatsApp, e quais os limites de envio?
2. O agente de IA entra antes, junto ou depois do wizard de emprestimo?
3. Ha conta Resend ativa, ou o e-mail deve sair do escopo?
4. Qual servidor recebera o deploy, e existe dominio disponivel?

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-16 | Criado apos a sessao identificar que decisoes de desenho foram tomadas sem conhecer integracoes existentes fora do repositorio. |
