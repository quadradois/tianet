# US-100 - Validar Modalidade por Tenant e Carteira

**ID:** US-100

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador de credito,
**quero** que a modalidade seja validada no meu Tenant e Carteira,
**para** impedir uso de parametro financeiro de outro escopo.

---

# 2. Critérios de Aceitação

- modalidade inexistente retorna `404` logico;
- modalidade de outro Tenant retorna `404` logico;
- modalidade de Carteira inacessivel retorna `404` logico;
- modalidade fora de vigencia nao pode ser usada em configuracao ativa futura.

---

# 3. Regras de Negócio Relacionadas

- Tenant e Carteira delimitam parametros financeiros;
- validacao de modalidade nao calcula parcelas nem saldo.

---

# 4. Dependências

- FEATURE-037 - Administrar Modalidades Financeiras;
- US-099 - Definir Modalidade Financeira Permitida;
- EPIC-006 - IAM.

---

# 5. Observações Técnicas

As respostas protegidas devem seguir a politica de isolamento ja usada no
backend: recurso invisivel por Tenant/Carteira responde `404`.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Validar Modalidade por Tenant e Carteira. |
