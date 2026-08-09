# PRODUCT-003 — Capability Administrar Comercial

**ID:** PRODUCT-003

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability é responsável por administrar o ciclo comercial de propostas e
simulações de crédito da plataforma.

Seu objetivo é permitir que o Credor avalie cenários, registre propostas
comerciais rastreáveis e decida se uma proposta aprovada seguirá para
formalização futura no contexto Contratos.

Esta Capability segue a hierarquia oficial de governança **Capability → Bounded
Context → EPIC → Feature → User Story** definida no FOUNDATION-009.

O contexto primário desta Capability é **Comercial**, atendido pelo
**EPIC-003 — Comercial / Propostas / Simulação**.

Nenhum cálculo financeiro definitivo pertence a esta Capability.

---

# 2. Valor de Negócio

Administrar Comercial estabelece a etapa de originação entre Cadastro e
Contratos.

Sem esta Capability, o Credor não possui uma trilha formal para simular,
analisar e aprovar uma proposta antes da formalização contratual. Ela reduz
retrabalho, evita que operações financeiras nasçam sem decisão comercial e
mantém a cadeia Cadastro → Comercial → Contratos → Motor Financeiro explícita.

---

# 3. Responsabilidades

Esta Capability é responsável por:

- criar e consultar simulações comerciais;
- criar propostas comerciais para Devedores ativos;
- consultar proposta por ID;
- listar propostas por Carteira, Devedor, estado e período;
- registrar decisões comerciais;
- aprovar, recusar, cancelar ou expirar propostas;
- disponibilizar proposta aprovada para o contexto Contratos futuro;
- registrar auditoria das escritas e transições comerciais;
- preservar isolamento por Tenant e Carteira em todas as operações.

---

# 4. Limites

Esta Capability não é responsável por:

- administrar Cadastro de Devedores;
- formalizar Contratos de Crédito;
- gerar documentos contratuais, assinatura ou liberação;
- administrar Empréstimos, Parcelas ou Pagamentos;
- calcular juros, amortização, saldo, quitação ou memória de cálculo;
- executar o Motor Financeiro;
- administrar Cobranças, Agenda ou Comunicação;
- integrar-se a bureaus de crédito, bancos, PIX ou provedores externos;
- administrar Usuários, Perfis e Permissões.

Essas responsabilidades pertencem às respectivas Capabilities e contextos do
produto.

---

# 5. Dependências

Esta Capability depende de:

- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-008 — Escopo do MVP;
- FOUNDATION-009 — Capability Map;
- ROADMAP-ALIGNMENT — documento oficial de transição do roadmap;
- AMP-001 — Architecture Master Plan;
- PRODUCT-001 — Capability Administrar Plataforma;
- PRODUCT-002 — Capability Administrar Cadastro;
- EPIC-001 — Gerenciar Tenant;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-020 — Aggregate Devedor.

---

# 6. Épicos

Esta Capability é atendida pelo seguinte Épico:

- **EPIC-003 — Comercial / Propostas / Simulação** (proposto; Bounded Context:
  Comercial).

---

# 7. Critérios de Aprovação

Esta Capability será considerada concluída quando:

- o EPIC-003 estiver implementado conforme a numeração global;
- simulações comerciais puderem ser criadas e consultadas;
- propostas comerciais puderem ser criadas, consultadas, listadas e decididas;
- apenas Devedores ativos da Carteira autenticada puderem originar propostas;
- proposta aprovada for disponibilizada como entrada para Contratos futuro;
- transições comerciais forem auditadas;
- o isolamento por Tenant/Carteira estiver garantido;
- nenhuma regra de cálculo financeiro definitivo estiver implementada no
  Comercial.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da Capability Administrar Comercial, materializada a partir do Discovery do EPIC-003 conforme FOUNDATION-009. |
