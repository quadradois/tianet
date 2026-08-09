# ADR-004: Autenticação e Autorização (IAM)

> **Status:** Aceito
> **Data:** 2026-08-08
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura
> **Aprovação:** Arquitetura / 2026-08-08
> **Substitui:** —
> **Substituído por:** —

---

## Contexto

Nenhum dos 14 endpoints da API exige autenticação, e nenhuma rota verifica a que
Tenant pertence o recurso acessado. O AMP-001 §2.6 registra a limitação
— *"Autenticação e autorização não implementadas. Endpoints administrativos
expostos sem IAM"* — e §11.2 a classifica como dívida perigosa, com o impacto
*"exposição de dados, acesso indevido"*.

Dois EPICs foram certificados nesse estado. O GATE-TECNICO-EPIC-002 §7 registra
a consequência: o EPIC-002 está *"certificado como funcionalidade, não como
pronto para dado real"*.

Esta ADR estava **reservada** desde o AMP-001 §8 com o escopo
*"JWT, RBAC, ABAC, OIDC, MFA — imediato, antes de produção real"*, sem conteúdo.
O Discovery do EPIC-006 levantou o material necessário para escrevê-la e tomou
duas decisões que aqui se formalizam.

### Fatores Relevantes

- **Técnicos:** o `Usuario` já existe no Platform Context com ciclo de vida
  (Convidado → Ativo → Inativo → Removido), mas **nenhuma coluna de credencial**
  existe em qualquer migration; o `perfil_acesso` é uma `String(50)` livre com um
  único valor em uso.
- **Negócio:** dado de devedor é dado de cliente do Tenant. Vazamento entre
  Tenants é falha de confidencialidade, não defeito funcional.
- **Organizacionais:** a ADR-001 §35 já fixou o mecanismo — *"JWT (Bearer Token)
  + Refresh Token — implementação pertence ao EPIC-006 e não será antecipada"*.
- **Temporais:** o AMP-001 §9.3 alerta que *"colocá-la depois exige reescrever
  todos os endpoints e testes"*. O custo já foi incorrido em dois EPICs; cada
  EPIC adicional o aumenta.

---

## Decisão

**Decidimos que** o IAM da plataforma se apoia em quatro definições:

### 1. Autenticação por JWT com refresh persistido

Token de **acesso** curto, autocontido e verificável criptograficamente sem consulta ao banco. A resolução do Principal e do RBAC consulta o estado corrente de Tenant, Usuário e Perfil para aplicar revogação imediata.
Token de **refresh** persistido e revogável, usado para renovar o acesso.

Formaliza a ADR-001 §35, que fixou "JWT + Refresh Token" sem dizer se o token
seria verificável offline ou consultado a cada requisição.

### 2. Validade do token de acesso: 15 minutos

O token de acesso expira em **15 minutos**; o refresh token, em **7 dias**.

O token não depende de uma Sessão persistida, mas Tenant, Usuário e Perfil são
resolvidos a cada operação. Assim, revogar o refresh bloqueia renovações e a
inativação de Tenant ou Usuário interrompe imediatamente novas requisições.
Os 15 minutos limitam a vida criptográfica do token e a exposição em caso de
furto da chave, sem substituir a validação do estado operacional corrente.

### 3. Autorização por RBAC

A autorização é decidida pelo **Perfil** do Usuário autenticado, conforme
FOUNDATION-009 §117, que já fixa *"autorização RBAC, perfis, permissões"* como o
modelo do contexto IAM. **ABAC está fora de escopo** — foi listado na reserva
desta ADR, mas o modelo aprovado é RBAC.

Há dois planos administrativos distintos. O **Administrador da Plataforma**
possui permissões globais `tenant.*`, opera a partir de um Tenant de controle
ativo e pode provisionar, listar, inativar e reativar outros Tenants. O
**Administrador do Tenant**, criado no provisionamento, recebe apenas permissões
operacionais do próprio Tenant e nunca `tenant.*`. A identidade inicial do
Administrador da Plataforma é responsabilidade de bootstrap operacional, não do
endpoint que provisiona clientes.

### 4. O IAM vive no Platform Context

Credencial, Perfil, Permissão e Sessão são artefatos de `domain/platform/`, ao
lado de Tenant e Usuário. **Não se cria um Bounded Context de IAM.**

Isto resolve uma contradição interna do AMP-001: §4.1 lista Autenticação,
Permissões e Perfis como responsabilidade **existente** do Platform Context,
enquanto §4.3 propõe um **IAM Context** classificado como *pós-MVP*. A segunda
leitura é incompatível com o tratamento de pré-requisito urgente que o roadmap
dá ao EPIC-006.

### Justificativa

O ponto que decide as quatro escolhas em conjunto é a **revogação**. O AMP-001
§3.1 promete que a inativação de Tenant revoga o acesso. Um JWT puramente
stateless não pode cumprir essa promessa antes de expirar. A solução escolhida
mantém a verificação criptográfica autocontida, mas resolve o estado corrente do
Principal e seu RBAC em cada requisição; a Sessão persistida continua reservada
ao refresh. Isso preserva tokens curtos e permite corte operacional imediato.

Quanto ao contexto: o `Usuario` já pertence ao Platform. Separar a credencial do
seu titular criaria uma fronteira e uma camada anticorrupção sem ganho no MVP.
FOUNDATION-009 §265 prevê exatamente este procedimento para épico transversal —
definir contexto primário e registrar dependências.

---

## Alternativas Consideradas

| Opção | Descrição | Prós | Contras | Por que não escolhida |
|-------|-----------|------|---------|----------------------|
| Sessão inteira no banco | Toda requisição exige uma Sessão ativa persistida | Revogação imediata e total | Acopla access token ao estado da Sessão | O desenho escolhido consulta o Principal/RBAC, mas não exige Sessão para validar o access token |
| JWT puro, sem estado | Nada persistido; o token carrega tudo | Máxima simplicidade e desempenho | **Revogação impossível** antes da expiração | Contraria a promessa do AMP-001 §3.1 de revogar tokens na inativação de Tenant |
| Bounded Context de IAM próprio | `domain/iam/` com ACL para o Platform | Isola a capacidade transversal | O AMP-001 §4.3 o classifica como pós-MVP; exigiria ACL sem ganho no MVP | Incompatível com a urgência do EPIC-006; o `Usuario` já vive no Platform |
| ABAC (autorização por atributo) | Decisão por atributos do recurso e do sujeito | Granularidade fina | Complexidade desproporcional ao MVP | FOUNDATION-009 §117 já fixa RBAC como o modelo |
| **Escolhida** | JWT curto + Principal/RBAC corrente + refresh revogável, dentro do Platform | Cumpre a revogação imediata; sem contexto novo | Consultas de autorização por requisição; tabela de refresh tokens | — |

---

## Consequências

### Positivas

- A inativação de Tenant ou Usuário passa a bloquear novas requisições imediatamente;
- O isolamento multi-tenant deixa de depender de disciplina: o Tenant vem do
  token e é verificado, não presumido;
- Nenhum Bounded Context novo — o modelo de domínio cresce onde já havia base;
- A trilha de auditoria (ADR-002) passa a registrar **quem** executou cada
  operação, não apenas o que aconteceu.

### Negativas / Riscos

- **Consulta do Principal e RBAC por requisição.** O corte imediato adiciona
  leituras no caminho de autorização.
  *Mitigação: consultas indexadas e possibilidade de cache curto em evolução futura.*
- **Retrofit em 14 endpoints.** Todos passam a exigir proteção.
  *Mitigação: as cinco rotas por `devedor_id` já convergem para uma única
  dependência (ADR-018), o que concentra boa parte do trabalho.*
- **Segredo de assinatura.** O JWT exige chave secreta, e hoje `.env.example` só
  contém `DATABASE_URL`.
  *Mitigação: a gestão do segredo entra no PLAN do EPIC-006; a chave nunca é
  versionada.*
- **O Platform Context cresce.** Concentra Tenant, Usuário, Configuração e agora
  Credencial, Perfil, Permissão e Sessão.
  *Mitigação: aceito no MVP; a extração permanece possível (ver Evolução).*

### Neutras / Trade-offs

- Renovação a cada 15 minutos gera tráfego adicional no endpoint de refresh —
  irrelevante na escala do MVP;
- Uma tabela nova (refresh tokens) e ao menos uma migration para a credencial.

---

## Plano de Implementação

| Etapa | Descrição | Responsável | Status |
|-------|-----------|-------------|--------|
| 1 | Fase de Product do EPIC-006 (Features e User Stories) | Produto | Concluído |
| 2 | Fase de Domínio (Credencial, Perfil, Permissão, Sessão) | Arquitetura | Concluído |
| 3 | PLAN-004 e execution backlog | Engenharia | Concluído |
| 4 | Implementação e retrofit dos endpoints | Engenharia | Concluído |

O detalhamento pertence ao PLAN-004; esta ADR fixa apenas as decisões.

---

## Métricas de Sucesso

| Métrica | Valor Alvo | Como Medir |
|---------|------------|------------|
| Endpoints protegidos | 13 de 14 (`/health` público) | Teste de contrato: requisição sem token responde 401 |
| Acesso cross-tenant | 0 | Teste de integração com dois Tenants reais |
| Janela de revogação | ≤ 15 min | Validade configurada do token de acesso |
| Credencial em texto legível | 0 ocorrências | Inspeção do schema e da trilha de auditoria |

---

## Evolução Esperada

A decisão de manter o IAM no Platform Context é adequada ao escopo atual, não
permanente. Quando SSO, federação de identidade (OIDC) ou MFA entrarem em
escopo — cenários que o AMP-001 §4.3 antecipa e que esta ADR deixa **fora** —,
a extração para um Bounded Context próprio deve ser reavaliada.

O contrato desta ADR permanece válido em qualquer dos cenários: o que mudaria é
onde o código mora, não como a autenticação e a autorização se comportam.

Igualmente, a validade de 15 minutos é um parâmetro operacional. Alterá-la não
requer nova ADR, desde que a mudança seja registrada e preserve os requisitos
de exposição criptográfica e renovação.

---

## Validação e Revisão

- **Critério de Aceitação da Decisão:** nenhum endpoint protegido acessível sem
  token válido; nenhum acesso cross-tenant possível; revogação de refresh
  interrompendo o acesso dentro da janela.
- **Data de Revisão Prevista:** quando SSO, OIDC ou MFA entrarem em escopo, ou
  na entrada da ADR-003 (nível de isolamento multi-tenant).
- **Responsável pela Revisão:** Arquitetura.

---

## Referências

- ADR-001 §35 — Stack Oficial: JWT (Bearer) + Refresh Token
- ADR-002 — Auditoria Independente da Transação
- ADR-018 — Identidade Externa do Devedor (dependência centralizada de rota)
- AMP-001 §2.6, §3.1, §4.1, §4.3, §8, §9.3, §11.2 — limitações, roadmap,
  contextos, reserva desta ADR, retrabalho e dívida
- FOUNDATION-006 — Arquitetura Multi-Tenant (Princípios 01-03)
- FOUNDATION-008 §3 — MVP inclui Usuários, Autenticação, Perfis, Permissões
- FOUNDATION-009 §117, §185, §265 — RBAC, IAM transversal, épico transversal
- PRODUCT-001 §85-87 — EPIC-006 é o IAM
- EPIC-006 Discovery §13.1 e §15 — origem das decisões aqui formalizadas
- GATE-TECNICO-EPIC-002 §7 — certificado como funcionalidade, não para dado real

---

## Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Decisão registrada — JWT curto com refresh revogável, RBAC, IAM no Platform Context, validade de 15 minutos. Materializa a reserva do AMP-001 §8. |
