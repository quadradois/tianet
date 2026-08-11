# US-101 - Criar Configuracao Financeira em Rascunho

**ID:** US-101

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador financeiro autorizado,
**quero** criar uma configuracao financeira em rascunho,
**para** preparar parametros antes de qualquer consumo por fluxos financeiros.

---

# 2. Critérios de Aceitação

- configuracao nasce obrigatoriamente como `rascunho`;
- `rascunho` nao pode ser retornado como configuracao vigente consumivel;
- configuracao registra Tenant, Carteira opcional, modalidade, parametros,
  calendario, vigencia, autoria e motivo;
- payload malformado retorna `400`.

---

# 3. Regras de Negócio Relacionadas

- configuracao em rascunho nao produz snapshot contratual;
- Configuracoes parametriza, Motor calcula.

---

# 4. Dependências

- FEATURE-038 - Parametrizar Politicas Financeiras;
- FEATURE-037 - Administrar Modalidades Financeiras.

---

# 5. Observações Técnicas

O PLAN deve prever testes para impedir que `rascunho` seja usado por Comercial,
Contratos ou Motor.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Criar Configuracao Financeira em Rascunho. |
