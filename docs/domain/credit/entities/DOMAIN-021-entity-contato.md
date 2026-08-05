# DOMAIN-021 — Entity Contato

**ID:** DOMAIN-021

**Versão:** 1.0.0

**Status:** Proposto

**Aggregate Pai:** DOMAIN-020 — Aggregate Devedor

---

# 1. Definição

O Contato representa um meio de comunicação do Devedor.

Ele concentra o canal (telefone, e-mail, WhatsApp), o valor do contato e a indicação de contato preferencial.

O Contato é tipado e possui ciclo de vida próprio dentro do cadastro do Devedor: pode ser adicionado, atualizado ou removido.

---

# 2. Identidade

Um Contato possui identidade única dentro do Devedor.

Um mesmo Devedor pode possuir vários Contatos, desde que a combinação de tipo e valor seja única dentro do cadastro.

---

# 3. Responsabilidades

O Contato é responsável por:

- representar um canal de comunicação do Devedor;
- armazenar o valor do contato (telefone, e-mail, WhatsApp);
- indicar o tipo de canal;
- sinalizar o contato preferencial;
- permitir atualização e remoção sem perda de histórico (auditoria da escrita).

O Contato não realiza cálculos financeiros.

O Contato não participa de operações de crédito.

---

# 4. Ciclo de Vida

## Criado

Contato adicionado ao cadastro do Devedor durante a criação ou atualização.

---

## Ativo

Contato válido e disponível para uso nos canais de comunicação.

---

## Removido

Contato removido do cadastro; permanece registrado na trilha de auditoria.

---

# 5. Regras

## RN-001

Todo Contato pertence exatamente a um Devedor.

---

## RN-002

Todo Contato possui um tipo (telefone, e-mail, WhatsApp).

---

## RN-003

Ao menos um Contato válido é obrigatório na criação do Devedor (RB-010 do Discovery do EPIC-002).

---

## RN-004

O valor do Contato deve ser válido para o tipo informado.

---

## RN-005

Apenas um Contato pode ser preferencial por tipo por Devedor.

---

## RN-006

A remoção de um Contato nunca elimina o histórico de auditoria.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-020 — Aggregate Devedor

---

## Relacionamentos

Devedor (1)

↓

Contato (0..N)

---

# 7. Invariantes

## INV-001

Todo Contato pertence exatamente a um Devedor.

---

## INV-002

Nenhum Contato pode existir sem tipo válido.

---

## INV-003

Nenhum Contato pode ser removido com perda do histórico de auditoria.

---

# 8. Glossário

## Contato

Meio de comunicação do Devedor (telefone, e-mail, WhatsApp).

---

## Contato Preferencial

Contato indicado como canal principal de comunicação com o Devedor.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da Entity Contato, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |
