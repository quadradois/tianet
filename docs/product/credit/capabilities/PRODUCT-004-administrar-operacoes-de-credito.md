# PRODUCT-004 - Capability Administrar Operacoes de Credito

**ID:** PRODUCT-004

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability e responsavel por administrar a formalizacao e a operacao de
credito no MVP.

Seu primeiro Epic atendido sera o EPIC-004 - Contratos de Credito. O ciclo
seguinte sera o EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro,
preservando a sequencia oficial do roadmap e mantendo Contratos sem calculos
financeiros definitivos.

---

# 2. Valor de Negocio

Administrar Operacoes de Credito transforma decisoes comerciais aprovadas em
instrumentos formais, auditaveis e preparados para originar operacoes
financeiras futuras.

Sem esta Capability, a plataforma possui proposta aprovada, mas nao possui
registro formal que possa servir de base para Emprestimos, Parcelas, Pagamentos
e Motor Financeiro.

---

# 3. Responsabilidades

Esta Capability e responsavel por:

- formalizar Contratos de Credito;
- preservar condicoes contratadas como snapshot historico;
- registrar assinatura ou formalizacao no MVP;
- consultar e listar contratos;
- liberar contrato formalizado como entrada logica para Motor Financeiro;
- criar Emprestimos a partir de contratos liberados;
- gerar Parcelas;
- registrar Pagamentos;
- consultar saldo e memoria de calculo;
- calcular quitacao e registrar renegociacao inicial;
- cancelar ou encerrar contratos conforme estado;
- auditar escritas e transicoes contratuais;
- preservar isolamento por Tenant e Carteira.

---

# 4. Limites

Esta Capability nao e responsavel por:

- liberar dinheiro ou integrar bancos/PIX;
- executar cobranca, agenda, comunicacao ou relatorios;
- administrar propostas comerciais;
- administrar Cadastro, IAM ou Plataforma.

---

# 5. Dependencias

Esta Capability depende de:

- FOUNDATION-007 - Product Map;
- FOUNDATION-008 - Escopo do MVP;
- FOUNDATION-009 - Capability Map;
- ROADMAP-ALIGNMENT - documento oficial de transicao do roadmap;
- AMP-001 - Architecture Master Plan;
- PRODUCT-001 - Capability Administrar Plataforma;
- PRODUCT-002 - Capability Administrar Cadastro;
- PRODUCT-003 - Capability Administrar Comercial;
- EPIC-001 - Gerenciar Tenant;
- EPIC-002 - Cadastro de Devedores;
- EPIC-003 - Comercial / Propostas / Simulacao;
- EPIC-006 - IAM;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao;
- DOMAIN-001 - Aggregate Carteira;
- DOMAIN-003 - Entity Contrato de Credito;
- DOMAIN-004 - Entity Emprestimo;
- DOMAIN-005 - Entity Parcela;
- DOMAIN-006 - Entity Pagamento;
- DOMAIN-010 - Service Motor Financeiro;
- DOMAIN-020 - Aggregate Devedor.

---

# 6. Epicos

Esta Capability sera atendida pelos seguintes Epicos:

- EPIC-004 - Contratos de Credito;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 7. Criterios de Aprovacao

Esta Capability sera considerada concluida no ciclo Contratos + Motor quando:

- contratos puderem ser criados somente a partir de propostas aprovadas;
- contratos puderem ser consultados e listados dentro da Carteira autenticada;
- assinatura/formalizacao for registrada de forma auditavel;
- contrato formalizado puder ser liberado como entrada logica para Motor futuro;
- contratos cancelados, encerrados ou liberados nao puderem ter parametros
  alterados indevidamente;
- Emprestimos nascerem somente de contratos liberados;
- Parcelas, Pagamentos, saldo, quitacao e memoria de calculo forem produzidos
  exclusivamente pelo Motor Financeiro;
- isolamento por Tenant/Carteira estiver garantido;
- nenhuma regra de calculo financeiro definitivo existir fora do Motor.

---

# 8. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-09 | Capability atualizada para incluir o EPIC-005 como ciclo planejado do Motor Financeiro. |
| 1.0.0 | 2026-08-09 | Primeira versao oficial da Capability Administrar Operacoes de Credito para iniciar EPIC-004. |
