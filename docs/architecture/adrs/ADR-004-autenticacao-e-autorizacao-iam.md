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

Token de **acesso** curto, autocontido e verificável sem consulta ao banco.
Token de **refresh** persistido e revogável, usado para renovar o acesso.

Formaliza a ADR-001 §35, que fixou "JWT + Refresh Token" sem dizer se o token
seria verificável offline ou consultado a cada requisição.

### 2. Validade do token de acesso: 15 minutos

O token de acesso expira em **15 minutos**; o refresh token, em **7 dias**.

Este número não é arbitrário: ele **é** a janela de revogação. Como o token de
acesso não é consultado no banco, revogar o refresh só interrompe o acesso na
próxima renovação — no pior caso, 15 minutos depois. Reduzir o valor encurta a
janela e aumenta a frequência de renovação; aumentá-lo faz o oposto.

### 3. Autorização por RBAC

A autorização é decidida pelo **Perfil** do Usuário autenticado, conforme
FOUNDATION-009 §117, que já fixa *"autorização RBAC, perfis, permissões"* como o
modelo do contexto IAM. **ABAC está fora de escopo** — foi listado na reserva
desta ADR, mas o modelo aprovado é RBAC.

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
§3.1 promete que a inativação de Tenant revoga tokens. Um JWT puramente
stateless não pode ser revogado antes de expirar — a promessa seria impossível
de cumprir. Verificar toda sessão no banco cumpriria, mas anularia a razão de
existir do JWT que a ADR-001 fixou.

O par "acesso curto sem estado + refresh com estado" é o desenho que satisfaz as
duas restrições, ao custo de uma janela de revogação explícita e mensurável.

Quanto ao contexto: o `Usuario` já pertence ao Platform. Separar a credencial do
seu titular criaria uma fronteira e uma camada anticorrupção sem ganho no MVP.
FOUNDATION-009 §265 prevê exatamente este procedimento para épico transversal —
definir contexto primário e registrar dependências.

---

## Alternativas Consideradas

| Opção | Descrição | Prós | Contras | Por que não escolhida |
|-------|-----------|------|---------|----------------------|
| Sessão inteira no banco | Todo token verificado contra o banco a cada requisição | Revogação imediata e total | Uma consulta por requisição em todo endpoint | Anula a razão de ser do JWT fixado na ADR-001 §35 |
| JWT puro, sem estado | Nada persistido; o token carrega tudo | Máxima simplicidade e desempenho | **Revogação impossível** antes da expiração | Contraria a promessa do AMP-001 §3.1 de revogar tokens na inativação de Tenant |
| Bounded Context de IAM próprio | `domain/iam/` com ACL para o Platform | Isola a capacidade transversal | O AMP-001 §4.3 o classifica como pós-MVP; exigiria ACL sem ganho no MVP | Incompatível com a urgência do EPIC-006; o `Usuario` já vive no Platform |
| ABAC (autorização por atributo) | Decisão por atributos do recurso e do sujeito | Granularidade fina | Complexidade desproporcional ao MVP | FOUNDATION-009 §117 já fixa RBAC como o modelo |
| **Escolhida** | JWT curto + refresh revogável, RBAC, dentro do Platform | Cumpre a revogação prometida; sem contexto novo | Janela de revogação de até 15 min; tabela de refresh tokens | — |

---

## Consequências

### Positivas

- A revogação prometida no AMP-001 §3.1 passa a ser implementável, com janela
  conhecida e documentada;
- O isolamento multi-tenant deixa de depender de disciplina: o Tenant vem do
  token e é verificado, não presumido;
- Nenhum Bounded Context novo — o modelo de domínio cresce onde já havia base;
- A trilha de auditoria (ADR-002) passa a registrar **quem** executou cada
  operação, não apenas o que aconteceu.

### Negativas / Riscos

- **Janela de revogação de até 15 minutos.** Um Tenant inativado ou um Usuário
  removido continua acessando até o token de acesso expirar.
  *Mitigação: a janela é curta e explícita; casos que exijam corte imediato
  precisam de verificação no banco, o que seria outra decisão.*
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
| 1 | Fase de Product do EPIC-006 (Features e User Stories) | Produto | Pendente |
| 2 | Fase de Domínio (Credencial, Perfil, Permissão, Sessão) | Arquitetura | Pendente |
| 3 | PLAN-004 e execution backlog | Engenharia | Pendente |
| 4 | Implementação e retrofit dos 14 endpoints | Engenharia | Pendente |

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
requer nova ADR, desde que a mudança seja registrada e a janela de revogação
resultante permaneça aceitável.

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
