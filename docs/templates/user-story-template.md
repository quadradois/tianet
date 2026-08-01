# US-[NNN]: [Título da User Story]

> **Status:** Proposto | Refinado | Pronto para Sprint | Em Andamento | Em Code Review | Em Validação | Concluído | Cancelado  
> **Feature Pai:** FEAT-[NNN]  
> **Épico Pai:** EPIC-[NNN]  
> **Prioridade:** Crítica | Alta | Média | Baixa  
> **Story Points:** [Valor: 1, 2, 3, 5, 8, 13, 21]  
> **Product Owner:** [Nome]  
> **Desenvolvedor:** [Nome]  
> **QA:** [Nome]  
> **Sprint:** [Identificador]  
> **Data de Criação:** YYYY-MM-DD  
> **Início:** YYYY-MM-DD  
> **Fim:** YYYY-MM-DD

---

## 1. Narrativa

> **Como** [persona/role]  
> **Quero** [ação/função específica]  
> **Para** [benefício/valor claro]

---

## 2. Critérios de Aceitação (ACs)

> Formato Given/When/Then (Gherkin)

### Cenário 1: [Nome do Cenário - Happy Path]

```gherkin
Given [pré-condição 1]
  And [pré-condição 2]
When [ação do usuário]
Then [resultado esperado 1]
  And [resultado esperado 2]
```

### Cenário 2: [Nome do Cenário - Fluxo Alternativo]

```gherkin
Given [pré-condição]
When [ação]
Then [resultado esperado]
```

### Cenário 3: [Nome do Cenário - Caso de Erro]

```gherkin
Given [pré-condição de erro]
When [ação]
Then [mensagem de erro esperada]
  And [comportamento do sistema]
```

---

## 3. Detalhamento Técnico (Opcional)

> Preencher durante o refinamento técnico / planning.

### 3.1 Tarefas de Implementação

| ID | Tarefa | Tipo | Estimativa (h) | Responsável | Status |
|----|--------|------|----------------|-------------|--------|
| TASK-001 | [Descrição] | Backend/Frontend/Infra/Teste | [Horas] | [Nome] | Pendente |
| TASK-002 | [Descrição] | Backend/Frontend/Infra/Teste | [Horas] | [Nome] | Pendente |

### 3.2 Componentes Afetados

- [Componente/Serviço 1]
- [Componente/Serviço 2]
- [Banco de Dados / Tabela]

### 3.3 Alterações de API / Contrato

- **Endpoint:** `[MÉTODO] /api/v1/[recurso]`
- **Mudança:** [Nova / Alteração / Depreciação]
- **Breaking Change:** Sim / Não

---

## 4. Design / UX (se aplicável)

- **Wireframe/Mockup:** [Link]
- **Estados:** [Lista de estados da tela]
- **Acessibilidade:** [Notas específicas]

---

## 5. Dados de Teste

| Cenário | Dados de Entrada | Resultado Esperado |
|---------|------------------|-------------------|
| Happy Path | [JSON/Descrição] | [JSON/Descrição] |
| Edge Case 1 | [JSON/Descrição] | [JSON/Descrição] |
| Error Case | [JSON/Descrição] | [Erro/Comportamento] |

---

## 6. Definition of Ready (DoR) — Checklist

- [ ] Narrativa clara e completa
- [ ] Critérios de aceitação escritos em Gherkin
- [ ] Dependências identificadas e resolvidas
- [ ] Design/UX aprovado (se aplicável)
- [ ] Estimativa de story points definida
- [ ] Tarefas técnicas identificadas
- [ ] Dados de teste preparados
- [ ] Critérios de performance/segurança definidos (se aplicável)

---

## 7. Definition of Done (DoD) — Checklist

- [ ] Código implementado e revisado (PR aprovado)
- [ ] Testes unitários passando (cobertura ≥ [X]%)
- [ ] Testes de integração passando
- [ ] Testes E2E passando (cenários AC cobertos)
- [ ] Build de CI/CD passando
- [ ] Deploy em ambiente de staging validado
- [ ] Validação de QA aprovada
- [ ] Documentação técnica atualizada
- [ ] Feature flag configurada (se aplicável)
- [ ] Métricas de observabilidade instrumentadas
- [ ] Rollback testado (se crítico)

---

## 8. Evidências de Validação

| Ambiente | Data | Validador | Resultado | Evidência (Link/Print) |
|----------|------|-----------|-----------|------------------------|
| Local | YYYY-MM-DD | [Nome] | Aprovado/Rejeitado | [Link] |
| Staging | YYYY-MM-DD | [Nome] | Aprovado/Rejeitado | [Link] |
| Produção | YYYY-MM-DD | [Nome] | Aprovado/Rejeitado | [Link] |

---

## 9. Histórico de Versões

| Versão | Data | Autor | Mudança |
|--------|------|-------|---------|
| 0.1.0 | YYYY-MM-DD | [Nome] | Criação inicial |

---

## 10. Anexos

- [Link para PR]
- [Link para branch]
- [Evidências de teste]
- [Notas de refinamento]