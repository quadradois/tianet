# DOMAIN-018 — Entity Usuário

**ID:** DOMAIN-018

**Versão:** 1.0.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-017 — Aggregate Tenant

---

# 1. Definição

O Usuário representa uma pessoa autorizada a acessar a plataforma em nome de um Tenant.

Seu papel é interagir com a plataforma conforme as permissões concedidas.

O Usuário pertence exclusivamente ao Platform Context.

Ele nunca pertence ao domínio financeiro.

---

# 2. Identidade

Um Usuário possui identidade única dentro de um Tenant.

Após sua criação, sua identidade permanece estável durante todo o seu ciclo de vida.

Um mesmo Usuário não poderá pertencer simultaneamente a dois Tenants.

---

# 3. Responsabilidades

O Usuário é responsável por:

- autenticar-se na plataforma;
- acessar os recursos autorizados;
- executar operações conforme suas permissões;
- manter seus dados cadastrais;
- registrar sua atividade para fins de auditoria.

O Usuário não executa regras financeiras.

O Usuário não é proprietário de operações de crédito.

---

# 4. Ciclo de Vida

## Convidado

Usuário criado, aguardando ativação.

---

## Ativo

Usuário habilitado para utilizar a plataforma.

---

## Inativo

Usuário temporariamente impedido de acessar a plataforma.

Seu histórico permanece preservado.

---

## Removido

Usuário desvinculado do Tenant.

Seu histórico de auditoria permanece preservado.

---

# 5. Regras

## RN-001

Todo Usuário pertence exatamente a um Tenant.

---

## RN-002

Todo Usuário deverá possuir um perfil de acesso.

---

## RN-003

Usuários somente poderão acessar recursos pertencentes ao seu Tenant.

---

## RN-004

A remoção de um Usuário nunca poderá eliminar registros históricos da plataforma.

---

## RN-005

Um Usuário poderá exercer diferentes papéis conforme suas permissões.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-017 — Aggregate Tenant

---

## Relacionamentos

Tenant (1)

↓

Usuário (0..N)

---

Usuário

↓

Perfis de Acesso

↓

Permissões

---

# 7. Invariantes

## INV-001

Todo Usuário pertence exatamente a um Tenant.

---

## INV-002

Nenhum Usuário poderá acessar recursos de outro Tenant.

---

## INV-003

Toda ação realizada por um Usuário deverá ser auditável.

---

# 8. Glossário

## Usuário

Pessoa autorizada a utilizar a plataforma.

---

## Perfil de Acesso

Conjunto de permissões concedidas ao Usuário.

---

## Auditoria

Registro das ações realizadas pelo Usuário dentro da plataforma.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Entity Usuário. |
