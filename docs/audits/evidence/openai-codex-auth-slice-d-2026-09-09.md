# Evidência sanitizada — autenticação OpenAI/Codex Slice D

**Data:** 2026-09-09  
**Escopo:** BFF, tela administrativa, contrato OpenAPI e jornada local com fake  
**Dados reais:** nenhum  
**Segredos ou códigos reais:** nenhum

## Resultado observado

A rota administrativa `/app/openai` consome somente a API TiaNet autenticada.
O BFF valida respostas com campos fechados, aceita o desafio apenas quando a URL
usa HTTPS no host exato `auth.openai.com` e nunca devolve token ao navegador.

A tela representa os oito estados públicos, inicia o device code por ação do
operador, oferece código copiável e link oficial, e consulta apenas o snapshot
local durante o polling. O polling começa a cada tentativa, termina no prazo do
desafio ou em dez minutos e não chama diagnóstico. Diagnóstico é uma ação
explícita, limitada visualmente por 60 segundos e também protegida no backend.
Logout e cancelamento removem a sessão local e não prometem revogação remota.

O snapshot OpenAPI foi regerado de forma determinística com **115 operações**,
**145 schemas** e SHA-256
`0d01766283ebe62c5cde983449e3028d710b6f6814d30e746850795cd730c059`.

## Verificações

- `api:check`, lint, typecheck e build do frontend: aprovados.
- Vitest: 1 teste unitário específico do desafio, 18 testes do componente;
  conjunto completo observado com 100 testes de componente; os conjuntos de
  BFF e contrato permanecem aprovados com 142 e 42 testes, respectivamente.
- Playwright com backend falso: 6 cenários aprovados em Chromium desktop e
  mobile, cobrindo login, polling, diagnóstico, logout, teclado, overflow e axe.
- Backend: snapshot determinístico, inventário e rotas OpenAI aprovados no
  conjunto focal.
- `docs:validate`, `docs:test` (incluindo 173/173 do PLAN-025),
  `harness:check` (139 checks) e `harness:test` (43 checks): aprovados.
- Revisão especializada `READ_ONLY`: aprovada após correções de ciclo de vida e
  revalidação do desafio recebido pela Server Action.

## Limites desta evidência

O fluxo usa somente fake local. Não houve login em conta real, inferência,
chamada de ferramenta, uso de cliente, deploy, commit ou push. A flag permanece
desligada. A prova assistida real pertence à Slice E.
