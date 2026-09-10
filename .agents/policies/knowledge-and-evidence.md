# Política de conhecimento e evidências

## Tipos de conhecimento

- **Produto:** o que o sistema deve fazer.
- **Domínio:** conceitos, relações, estados, eventos e invariantes do negócio.
- **Arquitetura:** estrutura, fronteiras, responsabilidades e dependências.
- **Decisão:** escolha aprovada e sua justificativa.
- **Design:** funcionamento pretendido de uma mudança específica.
- **Plano de execução:** ordem e verificações para implementar.
- **Invariante:** condição que não pode ser violada.
- **Risco:** evento incerto, impacto e mitigação.
- **Revisão:** crítica independente e sua adjudicação.
- **Evidência:** observação que sustenta uma afirmação.
- **Handoff:** estado operacional necessário à continuidade.

Não duplique a mesma definição em tipos diferentes. Aponte para a fonte responsável.

## Evidência mínima

Toda afirmação de conclusão relevante deve relacionar:

```text
Requisito → evidência esperada → check → resultado observado → status
```

Status permitidos: `VERIFICADO`, `VERIFICADO_COM_RESSALVAS`, `NÃO_VERIFICADO` e `BLOQUEADO`.

Um comando bem-sucedido não prova sozinho todos os requisitos. Registre qual risco ou comportamento cada check cobre.

## Conhecimento acumulado

Após mudança significativa, pergunte “o que aprendemos?” e converta apenas aprendizados duráveis em documentação, decisão, invariante, teste, lint, script ou regra. Não transforme incidentes isolados em regras universais.
