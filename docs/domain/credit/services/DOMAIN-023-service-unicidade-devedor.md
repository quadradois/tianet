# DOMAIN-023 — Domain Service UnicidadeDevedorService

**ID:** DOMAIN-023

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

O UnicidadeDevedorService é o Domain Service responsável por garantir a unicidade do documento do Devedor dentro da Carteira.

Ele verifica, antes da criação ou reativação de um cadastro, se já existe Devedor com o mesmo documento na mesma Carteira — independentemente do estado (Ativo ou Inativo).

Esta verificação reside no Domain para que a regra não dependa apenas de constraint de banco, permitindo mensagens de erro de negócio precisas e comportamento determinístico.

---

# 2. Responsabilidades

O UnicidadeDevedorService é responsável por:

- verificar se o documento informado já existe na Carteira;
- impedir a criação de Devedor duplicado;
- garantir a consistência da regra DOMAIN-024;
- apoiar a reativação, revalidando a unicidade do documento na Carteira (qualquer estado).

O serviço não persiste dados.

A persistência é responsabilidade do repositório.

---

# 3. Entradas

O UnicidadeDevedorService recebe:

- Documento (CPF) do Devedor;
- Identificador da Carteira.

---

# 4. Saídas

O UnicidadeDevedorService produz:

- Resultado indicando se o documento está disponível na Carteira;
- Sem efeitos colaterais de escrita.

---

# 5. Regras

## RN-001

Não pode existir mais de um Devedor com o mesmo documento na mesma Carteira (DOMAIN-024).

---

## RN-002

A verificação considera Devedores Ativos e Inativos.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do Domain Service UnicidadeDevedorService, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |