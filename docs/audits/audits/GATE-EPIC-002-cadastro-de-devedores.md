# GATE — EPIC-002 Cadastro de Devedores — Fechamento do Pacote SDD

**ID:** GATE-EPIC-002

**Versão:** 1.0.0

**Status:** Proposto — aguardando congelamento e aprovação para implementação

**Data:** 2026-08-05

**Escopo:** pacote documental SDD do EPIC-002 (Discovery → Domain → Product → Plan → Execution Backlog → Autoauditoria). **Sem código.**

---

# 1. Objetivo

Este Gate consolida o pacote documental do EPIC-002 — Cadastro de Devedores, após a
conclusão do Discovery, da modelagem de Domínio, da camada de Produto, do Plano Técnico
(PLAN-003) e do Backlog de Execução (PLAN-003-EXEC), e após a autoaditoria de consistência.

O resultado é o pacote SDD **congelado e aprovado para implementação** do próximo Agent
Loop, que executará exclusivamente as IMP-042..IMP-064.

---

# 2. Resumo Executivo

- **Estado do EPIC-002:** Pacote documental completo e consistente (0 erros de validação).
- **Features:** 4 (FEATURE-005..008).
- **User Stories:** 13 (US-015..US-027).
- **Regras de negócio e invariantes:** consolidados em DOMAIN-020..029.
- **Eventos de domínio:** 4 (DOMAIN-026..029).
- **Backlog de execução:** IMP-042..IMP-064 (23 tarefas), numeração contínua do EPIC-001.
- **Aderência:** FOUNDATION-009 (Capability → Contexto → EPIC), ROADMAP-ALIGNMENT-001 §10,
  AMP-001, FOUNDATION-008 (MVP).
- **Não implementado ainda:** nenhuma linha de código — conforme escopo autorizado.

---

# 3. Inventário dos Documentos Criados no EPIC-002

| Camada | Documento | ID |
|--------|-----------|----|
| Discovery | Discovery do EPIC-002 | `docs/audits/discoveries/EPIC-002-cadastro-de-devedores-discovery.md` |
| Product | PRODUCT-002 — Administrar Cadastro | `docs/product/credit/capabilities/PRODUCT-002-administrar-cadastro.md` |
| Product | EPIC-002 — Cadastro de Devedores | `docs/product/credit/epics/EPIC-002-cadastro-de-devedores.md` |
| Product | FEATURE-005 — Criar Devedor | `docs/product/credit/features/FEATURE-005-criar-devedor.md` |
| Product | FEATURE-006 — Consultar Devedor | `docs/product/credit/features/FEATURE-006-consultar-devedor.md` |
| Product | FEATURE-007 — Atualizar Devedor | `docs/product/credit/features/FEATURE-007-atualizar-devedor.md` |
| Product | FEATURE-008 — Inativar/Reativar Devedor | `docs/product/credit/features/FEATURE-008-inativar-reativar-devedor.md` |
| Product | US-015..US-027 (13 documentos) | `docs/product/credit/user-stories/US-015..US-027-*.md` |
| Domain | DOMAIN-020..029 (10 documentos) | `docs/domain/credit/{aggregates,entities,value-objects,services,rules,events}/DOMAIN-02*.md` |
| Implementation | PLAN-003 — Plano Consolidado | `docs/implementation/plans/PLAN-003-epic-002-cadastro-de-devedores.md` |
| Implementation | PLAN-003-EXEC — Backlog de Execução | `docs/implementation/backlogs/PLAN-003-execution-backlog.md` |
| Gate | Este documento | `docs/audits/audits/GATE-EPIC-002-*.md` |

**Total: 33 documentos** (1 Discovery + 19 Product + 10 Domain + 2 Implementation + 1 Gate).

---

# 4. Inventário de Features e User Stories

## FEATURE-005 — Criar Devedor

- US-015 — Criar Devedor;
- US-016 — Validar Dados Obrigatórios do Devedor;
- US-017 — Validar Unicidade do Documento;
- US-018 — Registrar Contatos do Devedor;
- US-019 — Registrar Auditoria do Cadastro;
- US-020 — Confirmar Criação do Devedor.

## FEATURE-006 — Consultar Devedor

- US-021 — Consultar Devedor por ID;
- US-022 — Consultar Devedor por Documento;
- US-023 — Listar Devedores;
- US-027 — Consultar Histórico Cadastral do Devedor (filigragem movida na auditoria — a Feature de leitura é a 006, não a 008).

## FEATURE-007 — Atualizar Devedor

- US-024 — Atualizar Dados Cadastrais do Devedor.

## FEATURE-008 — Inativar/Reativar Devedor

- US-025 — Inativar Devedor;
- US-026 — Reativar Devedor.

---

# 5. Regras de Negócio e Invariantes (Domínio — DOMAIN-020..029)

## Aggregate Devedor (DOMAIN-020)

- **INV-001** — Todo Devedor pertence exatamente a um Devedor Carteira.
- **INV-002** — O documento é único na Carteira (DOMAIN-024).
- **INV-003** — O documento é imutável após a criação.
- **INV-004** — O Devedor nunca perde histórico (DOMAIN-025).
- **INV-005** — Transições apenas entre **Ativo → Inativo → Ativo**.
- **INV-006** — Nenhum Devedor de um Tenant é acessível por outro (isolamento).
- **RN-001..RN-006** — regras operacionais associadas (vínculo à Carteira, CPF, pessoa física,
  sem exclusão física, inativo não origina, inativação preserva histórico).

## Entity Contato (DOMAIN-021) — RN-001..006 + INV-001..003

Unicidade tipo+valor por Devedor; ao menos um contato obrigatório (RB-010); preferencial
**um por tipo** (harmonizado na auditoria).

## Value Object Documento (DOMAIN-022)

- Normalização (somente dígitos), validação de CPF (dígitos verificadores), imutável.

## Domain Service UnicidadeDevedorService (DOMAIN-023)

- Verifica unicidade independente de estado; usado na criação e na reativação.

## Regras transversais

- **DOMAIN-024** — Documento único por Carteira (duas camadas: Domain + UNIQUE do repositório);
- **DOMAIN-025** — Exclusão física proibida.

---

# 6. Eventos de Domínio (DOMAIN-026..029)

| Evento | Origem | Emissor |
|--------|--------|---------|
| DOMAIN-026 | Devedor Cadastrado | Criação (Ativo) |
| DOMAIN-027 | Devedor Atualizado | Atualização cadastral |
| DOMAIN-028 | Devedor Inativado | Transição Ativo → Inativo |
| DOMAIN-029 | Devedor Reativado | Transição Inativo → Ativo |

Publicação em bus interno postergada para AMP-001 §3.1 (sem downstream acoplado nesta versão).

---

# 7. Modelo de Estados

```
            [criação]                    [inativação]                   [reativação]
                  │                           │                              │
       Devedor Ativo ────────────► Devedor Inativo ────────────► Devedor Ativo
                  │                           │
                  └──► Inicial = Ativo          └──► preserva histórico (RN-006)
```

- Estado inicial: **Ativo** (somente leitura após criação);
- Estado final Irreversível de exclusão: **inexistente** (proibido — DOMAIN-025).

Transições válidas: **Ativo → Inativo**, **Inativo → Ativo**. Qualquer transição a partir
de estado divergente → 409 `conflito_estado`.

---

# 8. Dependências

### Produto
- PRODUCT-002 (Administrar Cadastro); PRODUCT-001 (Administrar Plataforma — isolamento).

### Strategy
- FOUNDATION-006 (Multi-Tenant); FOUNDATION-007 (Product Map); FOUNDATION-008 (MVP);
  FOUNDATION-009 (Capability Map).

### Domain
- DOMAIN-001 (Carteira); DOMAIN-002 (Pessoa); DOMAIN-003..006/010 (crédito — referência);
  DOMAIN-017/018/019 (Platform — isolamento).

### Infraestrutura reutilizada (do EPIC-001, sem recriação)
- `SqlAlchemyUnitOfWork`, repositórios base, `Session`, ORM, `AuditoriaRegistro`
  (append-only), `IdempotenciaRegistro` (AD-002), exception handlers
  (400/404/409/422/500), DTO único (RA-012), Telemetry básica.

### Não resolvido nesta fase
- Autenticação/autorização (EPIC-006/IAM — fora do MVP deste EPIC);
- Publicação de eventos em bus (futuro).

---

# 9. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Duplicidade de Devedor por variação de CPF | Normalização + UNIQUE + UnicidadeDevedorService |
| Transições inválidas | Regra exclusiva no Domain + testes |
| Corrida em operações concorrentes | Transação única via UoW + constraint UNIQUE |
| Vazamento de dados pessoais (LGPD) | Isolamento via Carteira + DTO único |
| Exclusão acidental | Proibição de exclusão física (DOMAIN-025) |
| Auditoria incompleta | Eventos inicio/sucesso/falha nas escritas |
| Dependência de IAM não existente | Endpoints sem autorização (exposto até IAM); documentado |
| Estouro do escopo do MVP | Revisão contra FOUNDATION-008 nas quatro features |

Riscos da implementação final são tratados no PLAN-003-EXEC (PLAN).

---

# 10. Pendências e Não Escopos

### Pendências antes do próximo Agent Loop (lembradas para a transição)

1. **Validação de CPF** (dígito verificador) — entregue nos Unit de `VO Documento`
   (IMP-043) e no schema (adm. API).
2. **Integração com IAM/EPIC-006** — acréscimo posterior (identificação do usuário)
   fora do escopo desta fase.

### Não escopos declarados (documentados nas Features/U.S.)

- Autenticação por usuário (aguardar EPIC-006);
- integrações externas (bureaus);
- Propostas/Comercial/Contratos/Empréstimos (EPIC-003/004);
- cobranças.

---

# 11. Resultado da Autoauditoria (Fase D)

| Critério | Resultado |
|----------|-----------|
| Consistência Foundation → Domain → Product | ✔ |
| Aderência ao FOUNDATION-009 | ✔ (Capability → Bounded Context → EPIC → Feature → US) |
| Aderência ao ROADMAP-ALIGNMENT-001 §10 | ✔ (EPIC-002 Cadastro; numeração global) |
| Aderência ao AMP | ✔ (contexto Cadastro; sem cálculos financeiros) |
| Rastreabilidade completa | ✔ (0 US órfã; todas mapeadas) |
| IDs, links e referências | ✔ (0 erros `docs:validate`; ENT-001 é falso positivo do regex) |
| Conflitos documentais | 3 corrigidos na auditoria (filiação US-027, unicidade/reativação, preferencial por tipo) |
| Duplicidades | 1 editorial (RN-005/006 em 020 e 021, alinhado ao padrão); demais referências removidas |
| Aderência ao padrão EPIC-001 | ✔ (DTO único, padrão de erros, idempotência, auditoria) |

### Ajustes da autoauditoria (executados automaticamente)

1. **US-027** movida para **FEATURE-006** (era da FEATURE-008), alinhada ao PLAN-003 DA-306.
2. **DOMAIN-024/DOMAIN-023**: uniformização da verificação de unicidade na reativação
   (guarda defensiva consistente com "não podem existir dois Devedores com o mesmo doc").
3. **DOMAIN-021 RN-005 / PLAN-003** IMP-044: preferencial **por tipo** (antes, único global).
4. **DOMAIN-022** fonte "RB de cadastro" substituída por US-016 (rastreável).
5. **US-018** lista de canais consistente com DOMAIN-021 (telefone, e-mail, WhatsApp);
   IMP-044 idem.
6. **Typos editoriais** no US-020 corrigidos.

---

# 12. Critério de Recomendação (0 linha de código)

Este pacote **está pronto para congelamento e implementação.** Após a aprovação do SDD
e do ROADMAP-ALIGNMENT-001 (previsto), iniciar o **Agent Loop de implementação** executando
exclusivamente o PLAN-003-EXEC (IMP-042..IMP-064) — sem mudanças arquiteturais durante a implementação.

**Recomendação:** **aprovar para implementação** assim que o congelamento documental do pacote for
confirmado pelo responsável (dono do produto/arquitetura).

---

# 13. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão do Gate do EPIC-002 (relatório consolidado do pacote) SDD documental. |