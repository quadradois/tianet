# DOMAIN-022 — Value Object Documento

**ID:** DOMAIN-022

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Definição

O Documento representa a identificação civil oficial do Devedor.

Na versão 1 do produto, o Documento é o CPF de uma pessoa física (DOMAIN-002 RN-004).

O Documento é o dado que garante a unicidade do Devedor dentro da Carteira (DOMAIN-020 INV-002).

---

# 2. Imutabilidade

O Documento é imutável: uma vez atribuído a um Devedor, seu valor nunca pode ser alterado.

Novos valores não substituem o Documento cadastrado; uma eventual correção de dígito exige tratamento administrativo auditado, nunca edição direta do cadastro.

O Documento é armazenado normalizado (somente dígitos), preservando a comparabilidade e a unicidade.

---

# 3. Regras de Validação

| ID | Regra | Fonte |
|----|-------|-------|
| VO-022-VAL-001 | O Documento deve conter apenas dígitos (CPF). | DOMAIN-020 INV-002 |
| VO-022-VAL-002 | O Documento deve ser um CPF válido (dígitos verificadores corretos). | US-016 — dados obrigatórios (CPF válido) |
| VO-022-VAL-003 | O Documento é único dentro da Carteira. | DOMAIN-024 |
| VO-022-VAL-004 | O Documento não pode ser alterado após a criação. | DOMAIN-020 INV-003 |

---

# 4. Exemplos

| Situação | Valor | Válido? | Observação |
|----------|-------|---------|------------|
| CPF válido | 52998224725 | Sim | Dígitos verificadores corretos |
| CPF com dígito inválido | 11111111111 | Não | Repetição inválida |
| CPF duplicado na Carteira | 52998224725 | Não | Veda dois Devedores com o mesmo documento |
| Formato com máscara | 529.982.247-25 | Normalizado | Armazenado como 52998224725 |

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do Value Object Documento, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |