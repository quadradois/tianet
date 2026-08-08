# 2026-08-08 — Handoff: EPIC-002 Certificado — Encerramento do Ciclo de Cadastro

**Período coberto:** 2026-08-05 → 2026-08-08
**Status:** 🟢 EPIC-002 CERTIFICADO — implementação, testes, cobertura e migration verificados
**GATE:** `docs/audits/audits/GATE-TECNICO-EPIC-002-certificacao.md`
**Branch:** `master`

---

## 1. Estado Geral do Projeto

| Camada | Estado |
|--------|--------|
| Governança | Executável — `docs:validate` com 5 famílias de regras |
| Foundation | Congelada (FOUNDATION-001..009) |
| Domain | Congelada; Credit Context implementado até Devedor |
| Product | Congelada (4 capabilities, 8 features, 27 user stories) |
| Architecture | ADR-001, ADR-002, **ADR-018** (identidade externa do Devedor) |
| EPIC-001 | ✅ Certificado |
| EPIC-002 | ✅ **Certificado neste handoff** |

**Suíte:** 408 testes, 100% pass · cobertura 98% · `docs:validate` 0 erros · `docs:test` 42/42.

---

## 2. O que foi entregue no EPIC-002

Sete endpoints REST sob `/credit/carteiras/{carteira_id}/devedores`, cobrindo o
ciclo cadastral completo: criar, consultar por ID, consultar por documento,
listar com paginação e filtros, atualizar, inativar, reativar e consultar o
histórico.

| Feature | User Stories | Estado |
|---|---|---|
| FEATURE-005 — Criar Devedor | US-015..US-020 | ✅ |
| FEATURE-006 — Consultar Devedor | US-021, US-022, US-023, US-027 | ✅ |
| FEATURE-007 — Atualizar Devedor | US-024 | ✅ |
| FEATURE-008 — Inativar/Reativar | US-025, US-026 | ✅ |

Camadas: domínio (Aggregate Devedor, Contato, VO Documento, unicidade, 4 eventos),
aplicação (6 casos de uso), infraestrutura (repositórios, UoW, idempotência,
auditoria) e apresentação (rotas, schemas, dependências).

---

## 3. Decisões arquiteturais tomadas no período

| ID | Decisão |
|---|---|
| **ADR-018** | Identidade externa do Devedor é contextualizada pela Carteira. Aggregate Root não determina identidade externa da API. |
| **DA-002** | Nenhum EPIC com migration recebe GATE sem ciclo upgrade → validação → downgrade → upgrade executado. |
| **DA-099** | Defeito descoberto na certificação suspende o GATE; o teste permanece, o defeito vira backlog. |
| **GA-001** | Unicidade global de identificadores de governança. |
| **GP-001** | TASKs são efêmeras; rastreabilidade oficial é o commit, a ADR, o PLAN ou a Feature. |
| **AC-003** | O qualificador compõe o identificador: `TASK-092` e `TASK-092-A` são distintos. |

---

## 4. Defeitos encontrados e corrigidos

Os testes de integração da camada Application revelaram **dois defeitos de
produção** invisíveis às camadas anteriores. Detalhes no GATE §4.

| ID | Defeito | Impacto |
|---|---|---|
| TASK-099 | Contatos removidos permaneciam no banco — o `ContatoRepository` não tinha operação de remoção | Estado persistido divergia do Aggregate |
| TASK-100 | O escopo da Idempotency-Key era gravado e nunca lido | 409 indevido entre casos de uso distintos |

**Lição registrada:** os dois passaram por 371 testes porque as camadas anteriores
usavam dublês. Teste unitário confirma que `remover_contato` foi chamado; só o
teste de integração vê que a linha continua no banco.

---

## 5. Infraestrutura de governança construída

O período produziu, além do EPIC, três peças de governança — todas nascidas de
problemas concretos, não de princípio abstrato:

- **SPEC-001 + família Contracts:** o `docs:validate` passou a comparar conteúdo
  entre PLAN e PLAN-EXEC. Nasceu porque a divergência que originou a DR-001
  atravessou um congelamento sem alarme.
- **SPEC-002 + Identifier Registry:** 40 namespaces registrados com gramática,
  classe, fonte de governança e status. Nasceu porque uma colisão de
  identificadores quase foi publicada.
- **42 testes do próprio validador:** ele bloqueia commits, logo é software de
  produção.

Tags: `v0.2-architecture-frozen` (19bbd17) e `v0.3-governance-enforced` (07b51b7).

---

## 6. Riscos abertos

| Risco | Severidade | Observação |
|---|---|---|
| **Sem autenticação** | 🔴 Alta | Nenhum endpoint valida tenant ou usuário. O EPIC-002 está certificado como funcionalidade, **não** como pronto para dado real. |
| **Isolamento multi-tenant parcial** | 🔴 Alta | A pertinência Carteira↔Devedor é validada (ADR-018), mas não há verificação de que o Tenant é dono da Carteira. Depende do IAM. |
| **Numeração de EPICs ambígua** | 🟡 Média | [ROADMAP-ALIGNMENT](../../architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md) registra 10 conflitos entre PRODUCT-001 e AMP-001; a §5.2 propõe sequência única, mas as fontes ainda discordam. Resolver antes de abrir o próximo EPIC. |
| **Ordem de checagem divergente** | 🟢 Baixa | Dois serviços avaliam hash antes de estado, dois o inverso. Mensagens de erro diferentes para a mesma situação. Ver GATE §7.2. |
| **Núcleo do produto não implementado** | 🟡 Média | Contrato, Empréstimo, Parcela, Pagamento e Motor Financeiro existem em documentação, não em código. |

---

## 7. Próximo passo recomendado

A sequência oficial ([ROADMAP-ALIGNMENT §5.2](../../architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md))
coloca o **EPIC-006 (IAM)** imediatamente após o EPIC-001, classificado como
*"urgente — pré-requisito de segurança"*. Ele foi ultrapassado pelo EPIC-002 e
permanece pendente.

Recomendação da Engenharia, para decisão da Arquitetura:

1. **Resolver a numeração dos EPICs** — o conflito documentado bloqueia a
   abertura do próximo pacote sem ambiguidade;
2. **EPIC-006 (IAM)** — sem ele o backend não recebe dado real de cliente;
3. **EPIC-003/004/005** — o núcleo de crédito.

---

## 8. Estado do repositório

```
master              sincronizado com origin
tags                v0.2-architecture-frozen → 19bbd17
                    v0.3-governance-enforced → 07b51b7
testes              408 python · 42 validador
cobertura           98%
migrations          0001..0005 (0005 certificada em ciclo completo)
```

---

## 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Handoff de encerramento do EPIC-002 — certificado após ciclo de migration (DA-002) e correção de dois defeitos encontrados na certificação (DA-099). |
