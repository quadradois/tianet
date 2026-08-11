# FEATURE-037 - Administrar Modalidades Financeiras

**ID:** FEATURE-037

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Definir quais modalidades financeiras podem ser usadas no MVP e sob quais
condicoes de Tenant, Carteira e vigencia.

---

# 2. Valor de Negócio

Evita que Comercial, Contratos ou Motor recebam modalidades livres ou
divergentes, preservando uma linguagem financeira controlada.

---

# 3. Escopo

- criar e manter modalidades financeiras permitidas;
- vincular modalidade a Tenant e Carteira quando aplicavel;
- controlar disponibilidade por vigencia;
- impedir modalidade fora do catalogo oficial.

---

# 4. Fora do Escopo

- calcular parcela, juros, saldo ou quitacao;
- decidir credito;
- criar proposta, contrato ou emprestimo.

---

# 5. User Stories

- US-099 - Definir Modalidade Financeira Permitida;
- US-100 - Validar Modalidade por Tenant e Carteira.

---

# 6. Dependências

- EPIC-009 - Configuracoes Financeiras e Calendario Operacional;
- PRODUCT-009 - Administrar Configuracoes Financeiras;
- EPIC-005 - Motor Financeiro.

---

# 7. Critérios de Aprovação

- modalidade possui codigo, descricao, Tenant e escopo de Carteira quando
  aplicavel;
- modalidade indisponivel nao pode ser usada por nova configuracao;
- modalidade de outro Tenant ou Carteira inacessivel retorna `404` logico;
- nenhuma regra de calculo financeiro e executada nesta Feature.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Administrar Modalidades Financeiras. |
