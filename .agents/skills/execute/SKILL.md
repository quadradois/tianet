---
name: execute
description: Implemente um plano aprovado do TiaNet um slice por vez, com testes, revisão e atualização da verdade documental; é o único workflow que altera código de produção.
---

# Execute

## Propósito

Entregar cada slice aprovado com diff focal, testes proporcionais e documentação coerente.

## Quando usar

Use somente quando houver plano aprovado ou quando a tarefa estiver classificada como `TRIVIAL` ou `SMALL` e o processo mínimo estiver explícito.

## Quando não usar

Não use para explorar requisitos, escolher arquitetura ou executar trabalho bloqueado por decisão aberta.

## Entradas

- Plano e slice aprovados.
- Aceite, testes, invariantes e orçamento de mudança.
- Estado limpo ou alterações preexistentes compreendidas.

## Procedimento

1. Leia o plano, confirme status e verifique `git status --short`.
2. Declare objetivo, limites, arquivos esperados, riscos e checks do slice.
3. Implemente somente o necessário, preservando alterações alheias.
4. Escreva o menor teste capaz de provar o risco: unitário, integração, contrato, estrutural ou E2E.
5. Revise o diff antes dos checks e remova ruído acidental.
6. Execute checks; classifique falhas como introduzidas, preexistentes, ambientais ou ambíguas.
7. Faça revisão proporcional pelos ângulos necessários e adjudique cada achado.
8. Atualize plano, riscos, decisões, matriz de testes, progresso e documentos cuja verdade mudou.
9. Continue ao próximo slice apenas se o atual estiver verificado e o plano continuar válido.

## Saídas

Slice implementado, testes, revisão, evidências, plano atualizado e status factual.

## Gates

G6 antes da edição; G7 após diff completo; G8 após testes; G9 após revisão proporcional.

## Handoff

Entregue arquivos alterados, checks, resultados, riscos, regressões observadas e próximo slice para `$verify` ou para a próxima execução.

## Modos de falha

- Pare diante de redesign, expansão material de escopo, credencial, produção, destruição, migração de alto risco ou falha ambígua.
- Não faça commit, push, publicação ou ação externa sem pedido explícito.
- Não enfraqueça teste para fazê-lo passar.
- Não marque slice concluído quando código, testes, plano e documentação divergirem.
