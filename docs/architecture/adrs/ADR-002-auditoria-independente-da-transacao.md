# ADR-002: Auditoria Independente da Transação

> **Status:** Aceito
> **Data:** 2026-08-03
> **Autor(es):** Head de Produto
> **Revisor(es):** [Revisor(es)]
> **Aprovação:** Head de Produto / 2026-08-03
> **Substitui:** N/A
> **Substituído por:** N/A

---

## Contexto

O sistema precisa de uma trilha de auditoria confiável sobre as operações de escrita do
Platform Context (provisionamento de Tenant, atualizações cadastrais, inativações e
reativações). Em especial, o provisionamento (FEATURE-001, US-001) exige que cada passo do
processo — validação, criação de Carteira padrão, criação do primeiro Usuário
Administrador, inicialização de configurações, confirmação e falha — fique registrado.

O desafio é temporal: os registros de início, cada passo executado e falha/rollback devem
**sobreviver à transação de negócio**, inclusive quando a transação é revertida. Uma trilha
que fosse apagada no rollback não permitiria auditar tentativas mal-sucedidas.

### Fatores Relevantes

- **Técnicos:** transação única (AD-001) com commit no fim do processo; auditoria precisa
  existir fora do contexto do rollback para registrar falhas.
- **Negócio:** conformidade e rastreabilidade das operações administrativas da plataforma
  (melhora a conformidade do EPIC-001); necessidade de evidência mesmo em falhas.
- **Organizacionais:** decisão já adotada e implementada desde a FEATURE-001 (IMP-016,
  TASK-043), reutilizada por FEATURE-002/003/004; esta ADR apenas a formaliza.
- **Temporais:** vigente desde 2026-08-02; sem necessidade de reexecução técnica.

---

## Decisão

**Decidimos que:** a auditoria da plataforma é **independente da transação de negócio**:

- **Escrita é auditada:** toda operação de escrita (criação, atualização, inativação,
  reativação) registra eventos de auditoria de forma **append-only** e **imutável**
  (somente `INSERT` na tabela `audit_log`).
- **Leitura não é auditada:** operações de consulta (FEATURE-002) **não** geram trilha de
  auditoria — apenas escritas.
- **Sobrevivência ao rollback:** os eventos de auditoria são persistidos em **sessão própria**,
  com commit imediato, fora da sessão da transação de negócio. Registros de início,
  passo executado, falha e rollback **sobrevivem** a um rollback da transação de domínio
  (AD-001). Dessa forma, tentativas falhas podem ser auditadas.
- **Append-only:** a trilha não possui operações de UPDATE nem DELETE; cada evento é um novo
  registro com próprio identificador e instante.

### Justificativa

- Sessão própria com commit imediato garante que o evento de *falha/rollback* seja gravado
  mesmo quando a transação de negócio é revertida — a única opção que permite auditabilidade
  de tentativas mal-sucedidas em transação única (AD-001).
- O padrão append-only + carimbo de data/hora preserva a integridade e a ordem cronológica da
  evidência, essencial para conformidade (US-001 critério de auditoria, FEATURE-001).
- Separar a escrita da trilha do UoW de domínio (AD-001) mantém o Domain puro, sem acoplar a
  modelos de infraestrutura.

---

## Alternativas Consideradas

| Opção | Descrição | Prós | Contras | Por que não escolhida |
|-------|-----------|------|---------|----------------------|
| Auditoria na mesma sessão (tentada) | Interceptar o evento no mesmo UoW | Simplicidade de implementação | Rollback apaga a trilha da falha; perde a evidência de tentativas rejeitadas | Falha o requisito de falha registrável |
| Auditoria assíncrona (fila/mensageria) | Registrar eventos em fila assíncrona | Baixo impacto na escrita | Sem mensageria no MVP (ADR-001); posterga auditoria efetiva | Fora do escopo do MVP e sem trilha confiável de falha |
| Sessão de auditoria independente, append-only, commit imediato (Escolhida) | `audit_log` escrito em sessão própria, imutável, sobrevive ao rollback | Registro fiel mesmo em falha; append-only; domínio desacoplado | Sessão extra em cada evento | — |

---

## Consequências

### Positivas

- Auditoria confiável de tentativas de provisionamento, incluindo falhas e rollback (IMP-016).
- Base de conformidade para a plataforma (traça o histórico de escritas de Tenant).
- Reutilização transversal por FEATURE-003 (atualização) e FEATURE-004 (inativação/reativação) —
  todas as escritas futuras herdam o padrão.
- Domínio permanece desacoplado (Domain não conhece `audit_log`; o contrato é via porta
  `AuditoriaRegistro`).

### Negativas / Riscos

- Custo de escrever mais registros (início, passos, falha) — *Mitigação: trilha necessária
  só para operações de escrita; consultas não são auditadas (FEATURE-002).*
- Crescimento da tabela `audit_log` a longo prazo — *Mitigação: política de retenção/
  arquivamento registrada como dívida técnica; fora do MVP.*

### Neutras / Trade-offs

- A auditoria append-only não substitui a matriz de eventos do Domain; ambos convivem:
  eventos de domínio (DOMAIN-011..013) e trilha operacional são camadas distintas.

---

## Plano de Implementação

| Etapa | Descrição | Responsável | Prazo | Status |
|-------|-----------|-------------|-------|--------|
| 1 | Definir o conceito (escolha da alternativa) | Head de Produto | 2026-08-01 | Concluído |
| 2 | Implementar `audit_log` + porta `AuditoriaRegistro` (IMP-016) | Agente | 2026-08-01 | Concluído |
| 3 | Registrar eventos no fluxo de provisionamento (início/passos/sucesso/falha/rollback) | Agente | 2026-08-01 | Concluído |
| 4 | Formalizar esta ADR | Agente | 2026-08-03 | Concluído |

---

## Métricas de Sucesso

| Métrica | Valor Alvo | Como Medir | Frequência |
|---------|------------|------------|------------|
| Robustez em falha | Eventos de início/falha sobrevivem a rollback | Testes de integração (test_provisioning) | Por fase |
| Imutabilidade da trilha | Zero UPDATE/DELETE em produção | Revisão de schema/ORM | Por release |

---

## Validação e Revisão

- **Critério de Aceitação da Decisão:** auditoria persistida em `audit_log` sobrevive ao
  rollback da transação de negócio (verificado pelos testes de integração da FEATURE-001).
- **Data de Revisão Prevista:** 2026-08-10
- **Responsável pela Revisão:** Head de Produto

---

## Referências

- AD-004 — Auditoria (plano técnico da FEATURE-001) — origem desta decisão;
- ADR-001 — Stack Tecnológica Oficial do MVP;
- PLAN-001 — Plano Técnico da FEATURE-001 (AD-001/AD-002/AD-004);
- PLAN-001-EXEC — Backlog de Execução da FEATURE-001 (IMP-016);
- FEATURE-002 — Consultar Tenant (apenas escrita é auditada);
- FEATURE-003 — Atualizar Tenant;
- FEATURE-004 — Inativar/Reativar Tenant.

---

## Histórico de Versões

| Versão | Data | Descrição |
|-------|------|-----------|
| 1.0.0 | 2026-08-03 | Formalização da decisão de auditoria independente da transação (já vigente desde a FEATURE-001 / IMP-016). |

---

## Adendo 2026-08-27 — o agente do PLAN-033 nao muda esta decisao

Registrado pela Arquitetura via PLAN-033/IMP-358, sem reescrever o texto acima.

- **Leituras continuam fora da trilha.** As consultas que o copilot fizer a API
  sao leituras como quaisquer outras e **nao** geram `audit_log`.
- **Tool-calls do agente tem trilha propria, fora desta ADR.** O servico do
  agente registra entrada, ferramenta, campos autorizados e resultado resumido
  em log proprio, com o mascaramento da ADR-016 — e um log operacional do
  agente, nao a trilha de negocio.
- **Escritas disparadas pelo copilot entram na trilha normalmente**, com o
  `usuario_id` do Usuario copilot em `detalhes` (IMP-361), para que a autoria
  fique distinguivel da operadora humana.

