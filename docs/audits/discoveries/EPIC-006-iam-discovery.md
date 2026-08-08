# EPIC-006 — Product Discovery — IAM (Identidade e Controle de Acesso)

**ID:** EPIC-006

**Tipo:** Artefato de Discovery (engenharia de produto)

**Status:** Em revisão

---

# 1. Objetivo de Negócio

Habilitar o controle de identidade e acesso da plataforma: autenticar quem
opera, autorizar o que cada um pode fazer e garantir que nenhum Tenant alcance
dados de outro (FOUNDATION-006 Princípios 01-03).

Hoje **nenhum dos 14 endpoints exige autenticação**. Qualquer requisição acessa
qualquer Carteira de qualquer Tenant. O AMP-001 §2.6 registra isso como
limitação e §11.2 como dívida perigosa: *"Autenticação e autorização ausentes —
exposição de dados, acesso indevido"*.

Este épico é **pré-requisito de segurança para produção**
([ROADMAP-ALIGNMENT §5.2](../../architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md)),
não uma funcionalidade de negócio. Sem ele, o backend não pode receber dado real
de cliente — os EPIC-001 e EPIC-002 estão certificados como funcionalidade, não
como prontos para produção (GATE-TECNICO-EPIC-002 §7).

# 2. Valor Entregue ao Usuário

- O Credor acessa a plataforma com credencial própria, e apenas ele;
- Cada Tenant enxerga exclusivamente os próprios dados — o isolamento deixa de
  depender de disciplina e passa a ser verificado;
- Perfis distinguem o que cada Usuário pode fazer dentro do Tenant;
- A trilha de auditoria passa a registrar **quem** executou cada operação, e não
  apenas o que aconteceu;
- Sem este épico, todo endpoint construído a partir daqui nasce inseguro, e o
  retrabalho de retrofit cresce a cada EPIC (AMP-001 §9.3).

# 3. Escopo

- Autenticar Usuário por credencial e emitir token de acesso;
- Renovar sessão sem novo login (refresh);
- Encerrar sessão;
- Registrar e alterar credencial do Usuário;
- Definir Perfis de Acesso e as Permissões de cada Perfil;
- Atribuir Perfil a Usuário dentro do Tenant;
- Autorizar cada operação conforme o Perfil do Usuário autenticado (RBAC);
- Propagar o Tenant autenticado a toda requisição e recusar acesso a recursos de
  outro Tenant;
- Auditar eventos de acesso (login, falha de login, negação de autorização);
- Gerir o ciclo de vida do Usuário (Convidado → Ativo → Inativo → Removido),
  hoje existente no modelo mas nunca transicionado fora do provisionamento.

# 4. Fora do Escopo

- SSO e federação de identidade (OIDC) — previstos apenas na reserva da ADR-004
  (AMP-001 §8), sem especificação;
- MFA — idem;
- ABAC (autorização por atributo) — o modelo decidido é **RBAC**
  ([FOUNDATION-009 §117](../../foundation/FOUNDATION-009-capability-map.md));
- Autoatendimento de recuperação de senha por e-mail — depende de Notification
  Service (ADR-009, pós-MVP);
- Gestão de Configurações da Plataforma — capability própria, sem EPIC atribuído
  (PRODUCT-001 §89);
- Revogação de token na inativação de Tenant — prevista em AMP-001 §3.1, mas
  depende de decisão sobre estratégia de sessão (ver §13 Riscos);
- Autenticação de sistemas externos (API keys, service accounts).

# 5. Linguagem Ubíqua (termos do contexto IAM)

| Termo | Significado no contexto |
|---|---|
| **Credencial** | Meio pelo qual o Usuário comprova sua identidade |
| **Sessão** | Período autenticado, representado por um token com validade |
| **Token de Acesso** | Credencial de curta duração apresentada a cada requisição |
| **Refresh Token** | Credencial de duração maior, usada para renovar o acesso sem novo login |
| **Perfil de Acesso** | Conjunto nomeado de Permissões atribuível a um Usuário |
| **Permissão** | Autorização para executar uma operação específica |
| **Autenticação** | Estabelecer quem é o Usuário |
| **Autorização** | Decidir se o Usuário autenticado pode executar a operação |
| **Principal** | O Usuário autenticado e seu Tenant, propagados na requisição |

Nenhum termo global da Linguagem Ubíqua (FOUNDATION-002) é redefinido. `Usuario`
e `Tenant` mantêm o significado atual.

# 6. Atores

- **Administrador do Tenant** — autentica-se, administra Usuários e Perfis
  dentro do seu Tenant;
- **Usuário operador** — autentica-se e opera conforme o Perfil recebido;
- **Sistema** — valida token e resolve o Principal a cada requisição.

Não há ator "Administrador da Plataforma" cross-tenant neste escopo: o
isolamento entre Tenants é absoluto (FOUNDATION-006 Princípio 02).

# 7. Casos de Uso

Numeração seguindo a sequência do namespace `UC`, que vai até UC-008
(EPIC-001). Os identificadores definitivos são emitidos na Fase de Product,
conforme o Registry (SPEC-002).

| ID | Caso de uso |
|---|---|
| UC-020 | Autenticar com credencial e receber token |
| UC-021 | Renovar token de acesso |
| UC-022 | Encerrar sessão |
| UC-023 | Definir credencial inicial do Usuário |
| UC-024 | Alterar a própria credencial |
| UC-025 | Criar e manter Perfis de Acesso |
| UC-026 | Atribuir Perfil a Usuário |
| UC-027 | Autorizar operação conforme Perfil |
| UC-028 | Resolver o Tenant do Principal e barrar acesso cruzado |
| UC-029 | Transicionar estado do Usuário (ativar, inativar, remover) |

# 8. Regras de Negócio

- Toda requisição a endpoint protegido exige token válido;
- Token expirado ou inválido não concede acesso;
- Apenas Usuário em estado **Ativo** autentica (o modelo já prevê o estado —
  `usuario.py:18-24` — mas hoje nenhum fluxo o transiciona);
- Credencial nunca é armazenada em texto legível;
- Usuário pertence a exatamente um Tenant (INV-001 de DOMAIN-018) e só acessa
  recursos desse Tenant;
- Permissão é verificada por operação, não por recurso individual (RBAC);
- Falha de autenticação não revela se o identificador existe;
- Eventos de acesso são auditados na trilha append-only (ADR-002).

# 9. Máquina de Estados

O ciclo do Usuário **já existe** em DOMAIN-018 (`usuario.py:18-24`):

```
Convidado → Ativo → Inativo → Removido
```

O IAM passa a operá-lo: hoje o Usuário nasce Convidado no provisionamento
(`tenant.py:166-180`) e permanece assim indefinidamente, porque nenhum caso de
uso o transiciona. Definir credencial é o evento natural de ativação.

Sessão tem ciclo próprio a definir na Fase de Domínio: emitida → válida →
expirada/revogada.

# 10. Invariantes

- Todo Usuário pertence a exatamente um Tenant (DOMAIN-018 INV-001);
- Todo Principal autenticado carrega Tenant e Usuário resolvidos;
- Nenhuma operação executa sem Principal em endpoint protegido;
- Nenhum acesso atravessa a fronteira de Tenant (FOUNDATION-006 Princípio 03);
- Credencial não é recuperável, apenas redefinível.

# 11. Eventos de Domínio

Candidatos, a formalizar na Fase de Domínio:

- Usuário autenticado;
- Tentativa de autenticação recusada;
- Credencial definida ou alterada;
- Perfil atribuído a Usuário;
- Autorização negada;
- Sessão encerrada.

# 12. Integrações

- **Todos os contextos** consomem o IAM para isolamento e autorização
  (FOUNDATION-009 §185) — é o épico mais transversal do sistema;
- **Platform** fornece Tenant e Usuário, que já existem;
- **Auditoria** (ADR-002) recebe os eventos de acesso pela infraestrutura
  existente;
- Nenhuma integração externa no escopo.

# 13. Riscos

| Risco | Observação |
|---|---|
| **Retrofit em 14 endpoints** | Todos os endpoints existentes passam a exigir proteção. AMP-001 §9.3 registra que adiar aumenta o retrabalho — o custo já foi incorrido em dois épicos |
| ~~Estratégia de sessão indefinida~~ | **Decidida** — ver §13.1 |
| **Onde mora a credencial** | Coluna em `usuario` ou entidade separada — decide o modelo de domínio e a migration. A decidir na Fase de Domínio |
| ~~IAM como Bounded Context~~ | **Decidido** — Platform Context, ver §15 |
| **Segredo de assinatura** | JWT exige chave secreta; hoje `.env.example` só tem `DATABASE_URL`. Gestão de segredo é decisão de infraestrutura |
| **Ordem de execução** | O épico foi ultrapassado pelo EPIC-002; quanto mais épicos avançam sem IAM, maior o retrofit |

## 13.1 Estratégia de sessão: JWT curto + refresh com estado (decidida)

A ADR-001 §35 fixa **JWT (Bearer) + Refresh Token**, mas não diz se o token é
verificável offline ou consultado a cada requisição. Essa lacuna importa porque
o AMP-001 §3.1 promete *"revogação de tokens"* na inativação de Tenant — e um
JWT puramente stateless não pode ser revogado antes de expirar.

**Decisão:** token de acesso **curto e sem estado**; refresh token
**persistido e revogável**.

| Alternativa | Por que não |
|---|---|
| JWT puro, sem estado | Impossível revogar: um Tenant inativado continuaria operando até o token vencer, contrariando o AMP-001 §3.1 |
| Sessão inteira no banco | Uma consulta por requisição — anula a razão de ser do JWT fixado na ADR-001 |

Consequências: a revogação corta o acesso na próxima renovação, deixando uma
janela igual à validade do token de acesso; essa validade passa a ser um
parâmetro de segurança relevante e deve ser fixada na ADR-004. Exige uma tabela
de refresh tokens e a respectiva migration.

# 14. Dependências

Esta Discovery depende de:

- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03, isolamento);
- FOUNDATION-008 — MVP Scope (§3 inclui Usuários, Autenticação, Perfis, Permissões);
- FOUNDATION-009 — Capability Map (§117 fixa RBAC; §185 IAM é transversal);
- PRODUCT-001 — Administrar Plataforma (§85-87, IAM é o EPIC-006);
- ADR-001 — Stack Oficial (§35 fixa JWT Bearer + Refresh Token);
- DOMAIN-017 — Aggregate Tenant; DOMAIN-018 — Entity Usuario;
- ADR-002 — Auditoria Independente da Transação;
- ADR-018 — Identidade externa do Devedor (a validação de pertinência já está
  centralizada, ver §16).

# 15. Fronteiras do Bounded Context (IAM)

O IAM é **transversal**: todo contexto o consome (FOUNDATION-009 §185), mas ele
não consome nenhum contexto de negócio. Depende apenas de Platform, de onde vêm
Tenant e Usuário (AMP-001 §6.1).

## Contexto primário: Platform (decidido)

O AMP-001 se contradizia: §4.1 lista Autenticação, Permissões e Perfis dentro do
**Platform Context** (existente); §4.3 propõe um **IAM Context** separado,
classificado como *pós-MVP*.

**Decisão: o IAM é entregue dentro do Platform Context.** Credencial, Perfil,
Permissão e Sessão são artefatos de `domain/platform/`, ao lado de Tenant e
Usuário — que já vivem lá e são a base do modelo.

Justificativa:

- é a leitura do §4.1, que trata desses temas como responsabilidade **existente**
  do Platform;
- o §4.3 classifica o IAM Context como **pós-MVP**, incompatível com o
  tratamento de pré-requisito urgente que o roadmap lhe dá — adotá-lo exigiria
  reclassificar a própria seção;
- o `Usuario` já pertence ao Platform; separar a credencial do seu titular
  criaria uma fronteira e uma ACL sem ganho no MVP;
- FOUNDATION-009 §265 pede exatamente isto para épico transversal: **definir
  contexto primário** e registrar dependências.

A extração para um Bounded Context próprio permanece possível quando SSO, MFA ou
federação entrarem em escopo — cenários que o §4.3 antecipa e que hoje estão
fora (§4).

# 16. Relação com o trabalho já entregue

A ADR-018 preparou o terreno de forma verificável:

- as sete rotas de Devedor são aninhadas sob `/carteiras/{carteira_id}`, então o
  Tenant é resolvível a partir da URL;
- as cinco rotas por `devedor_id` (consulta, histórico, atualização, inativação
  e reativação) passam por **uma única dependência**
  (`get_devedor_da_carteira`, `dependencies.py:194-218`) — a verificação de
  Tenant entra ali e cobre todas de uma vez;
- a ADR-018 §"Evolução Esperada" antecipa este momento: *"quando a arquitetura
  incorporar autenticação, autorização e filtros multi-tenant na camada de
  persistência, essa validação poderá ser absorvida pelo repositório"*.

Lacunas concretas no código, levantadas nesta Discovery:

- `usuario` **não tem coluna de credencial** em nenhuma migration (`0001` cria a
  tabela, `0002` acrescenta `perfil_acesso`) — exige migration nova;
- `UsuarioRepository` não tem `find_by_email` (`repositories/__init__.py:142-169`)
  — necessário para autenticar;
- `perfil_acesso` é `String(50)` livre, com um único valor em uso
  (`"administrador"`) — não é estrutura RBAC;
- não existe nenhum código de token, header `Authorization` ou middleware.

# 17. Autoavaliação de Consistência

| Verificação | Resultado |
|-------------|-----------|
| Conflito com fontes oficiais | Nenhum — EPIC-006 = IAM está alinhado em PRODUCT-001 v2.0.0, FOUNDATION-009 e ROADMAP-ALIGNMENT §5.2 |
| Necessidade de alterar FOUNDATION | Não — FOUNDATION-006/008/009 já preveem Autenticação, Perfis e Permissões no MVP |
| Necessidade de ADR nova | **Sim — ADR-004**, reservada em AMP-001 §8 e ainda sem conteúdo. Deve formalizar as decisões de §13.1 e §15 e fixar a validade do token de acesso |
| Mudança de Bounded Context ou Capability | **Decidido** — Platform Context (§15). Nenhum contexto novo; FOUNDATION-009 §265 aplicado |
| Conflito de linguagem ubíqua | Não — termos novos confinados ao contexto IAM |
| Dúvida sobre Core Domain | Não — Motor Financeiro permanece o único Core Domain |
| Decisões irreversíveis | **Resolvida** — estratégia de sessão definida em §13.1 (JWT curto + refresh com estado) |
| Escopo do épico (conflito CP-006) | **Resolvido** — PRODUCT-001 v2.0.0 adotou o escopo amplo: Usuários, Perfis e Permissões integram o EPIC-006 |
| Contradição interna do AMP-001 (§4.1 × §4.3) | **Resolvida** por decisão de contexto primário (§15). O AMP-001 deve ser atualizado quando a ADR-004 for emitida |

**Conclusão da autoavaliação:** o Discovery é consistente com a governança
congelada. As duas condições de parada originais — contexto primário e
estratégia de sessão — **foram decididas** (§15 e §13.1) e devem ser
formalizadas na **ADR-004**, único artefato de Arquitetura ainda pendente.

A Fase de Product (EPIC-006, Features, User Stories) pode prosseguir
imediatamente. A Fase de Domínio depende da ADR-004, que agora tem conteúdo
definido para registrar.

---

# User Stories Candidatas

Identificação preliminar, a materializar na Fase de Product:

- **FEATURE-009 — Autenticar Usuário:** autenticar com credencial; renovar
  sessão; encerrar sessão; recusar credencial inválida sem revelar existência;
- **FEATURE-010 — Gerir Credenciais:** definir credencial inicial (ativando o
  Usuário); alterar a própria credencial; redefinir credencial de Usuário do
  Tenant;
- **FEATURE-011 — Gerir Perfis e Permissões:** criar e manter Perfis; atribuir
  Perfil a Usuário; consultar Permissões efetivas;
- **FEATURE-012 — Autorizar Requisição:** validar token e resolver o Principal;
  autorizar operação conforme Perfil; barrar acesso a outro Tenant; auditar
  acesso negado.

A numeração de Features e User Stories deve ser emitida conforme o Registry
(SPEC-002): FEATURE está em 008 e US em 027 no momento desta Discovery.

Critérios de aceitação transversais propostos:

- endpoint protegido sem token válido responde 401; token válido sem permissão
  responde 403;
- recurso de outro Tenant responde 404, não 403 — não revelar existência,
  coerente com o precedente da ADR-018;
- credencial nunca trafega nem é persistida em texto legível;
- evento de acesso auditado na trilha append-only (ADR-002);
- `/health` permanece público.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 0.1.0 | 08/08/2026 | Primeira versão do Discovery do EPIC-006 — IAM, para revisão arquitetural (ciclo SDD + Agent Loop). |
