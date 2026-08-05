# FEATURE-007 — Atualizar Devedor

**ID:** FEATURE-007

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável pela atualização dos dados cadastrais do Devedor.

Seu objetivo é permitir a alteração do nome e do conjunto de contatos, preservando os dados imutáveis — documento e vínculo com a Carteira.

---

# 2. Valor de Negócio

Esta Feature garante a manutenção da qualidade cadastral e da comunicação com o Devedor.

Dados atualizados são pré-requisito para Comunicação, Agenda e Cobrança futuras.

---

# 3. Escopo

Esta Feature contempla:

- atualizar o nome do Devedor;
- adicionar, alterar e remover contatos;
- alterar o contato preferencial;
- validar a unicidade e a integridade dos dados alterados;
- registrar auditoria da alteração.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- alteração do documento (CPF) — imutável;
- alteração do vínculo com a Carteira;
- inativação/reativação (FEATURE-008);
- exclusão do cadastro;
- qualquer cálculo financeiro.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-024 — Atualizar Dados Cadastrais do Devedor.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro;
- DOMAIN-020 — Aggregate Devedor;
- DOMAIN-021 — Entity Contato;
- DOMAIN-022 — Value Object Documento (imutabilidade);
- ADR-002 — Auditoria Independente da Transação;
- AD-001 — Transação única no MVP.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- nome e contatos puderem ser atualizados com segurança;
- documento e vínculo com a Carteira permanecerem imutáveis;
- a alteração estiver registrada para auditoria;
- Devedor inexistente retornar 404;
- todas as User Stories estiverem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da Feature Atualizar Devedor, criada no ciclo SDD do EPIC-002. |