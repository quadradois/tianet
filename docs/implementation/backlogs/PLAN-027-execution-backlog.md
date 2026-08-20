# PLAN-027-EXEC - Backlog do Wizard de Lancamento

**ID:** PLAN-027-EXEC

**Versao:** 1.6.0

**Status:** IMP-305, IMP-306, IMP-308..IMP-311 concluidos; IMP-307 planejado

---

# 1. Contexto

Ordem executavel do PLAN-027. A numeracao continua apos IMP-304, ultimo item do
PLAN-025.

O ciclo materializa o caminho unico de lancamento: uma operacao de backend
atomica, o wizard que a consome e as duas telas de leitura pedidas pelo Credor.
Nada e removido — as telas passo a passo continuam alcancaveis, e a Proposta com
aprovacao permanece porque e a caixa de entrada do agente de IA
(`FOUNDATION-001 §3.1`).

---

# 2. Fase A - Backend

### IMP-305 - Servico de lancamento composto

- **Objetivo:** servico de aplicacao que, sob um unico `UnitOfWork`, resolve ou
  cria o Devedor, percorre Proposta e Contrato pelos metodos de agregado, cria o
  Emprestimo e gera o plano de parcelas, com um commit unico.
- **Componentes afetados:** `src/emprestimo/application/lancamento.py`,
  `tests/integration/application/test_lancamento.py`.
- **Dependencias:** nenhuma.
- **Criterios de conclusao:** invariantes executadas pelos metodos de agregado
  com `usuario_id`, nunca contornadas; trilha de auditoria completa; falha em
  qualquer passo desfaz tudo; nenhum calculo financeiro fora do Motor.
- **Suite minima:** integracao contra PostgreSQL real, com rollback exercitado
  passo a passo.
- **Status:** Concluido.
- **Nota de execucao:** o guardrail de exclusividade do Motor
  (`test_motor_exclusivity_guardrails.py`) proibe qualquer modulo fora do Motor
  de importar `motor_financeiro`. O orquestrador recebe a etapa financeira por
  injecao (`CriadorDeEmprestimo`) e nao referencia o Motor em nenhum ponto; a
  criacao do Emprestimo e a geracao do plano vivem em
  `application/motor_financeiro.criar_emprestimo_e_plano_em`, que aceita um
  `UnitOfWork` ja aberto.

### IMP-306 - Endpoint de lancamento

- **Objetivo:** expor a operacao em
  `POST /credit/carteiras/{carteira_id}/lancamentos`, com `Idempotency-Key`
  obrigatoria.
- **Componentes afetados:** `presentation/api/lancamento_routes.py`,
  `presentation/api/lancamento_schemas.py`, `presentation/api/main.py`,
  `presentation/api/openapi.py`, snapshot OpenAPI governado.
- **Dependencias:** IMP-305.
- **Criterios de conclusao:** replay com a mesma chave devolve o resultado
  original; payload divergente com a mesma chave e conflito; RBAC exige as
  permissoes de Devedor, Comercial, Contratos e Motor; contagem de operacoes do
  snapshot atualizada de forma explicita.
- **Suite minima:** integracao de API, contrato e idempotencia.
- **Status:** Concluido.
- **Nota de execucao:** o inventario passou de 107 para 108 operacoes e de 133
  para 137 schemas. O snapshot governado foi regerado (byte a byte com o
  runtime, por contrato), o cliente tipado do frontend foi regenerado e os pinos
  de contagem, SHA e header idempotente foram avancados deliberadamente. A
  matriz permanece em 107: nenhuma jornada frontend consome a operacao nova
  ainda, e ela entra na matriz no IMP-308.

### IMP-307 - Comprovante do lancamento

- **Objetivo:** gerar no backend o texto do comprovante e enfileirar o envio
  fora da transacao do lancamento.
- **Componentes afetados:** `application/comprovante.py`,
  `domain/credit/operacao_diaria.py` (valor `whatsapp` em `CanalComunicacao`),
  migration aditiva.
- **Dependencias:** IMP-305.
- **Criterios de conclusao:** o texto usa somente valores retornados pelo Motor;
  o envio nao bloqueia o commit; falha de canal nao desfaz o lancamento.
- **Suite minima:** unidade da montagem do texto, integracao do enfileiramento.
- **Status:** Planejado.

---

# 3. Fase B - Frontend

### IMP-308 - Wizard de lancamento

- **Objetivo:** tres passos — Devedor, Condicoes, Confirmacao — com uma unica
  chamada ao endpoint.
- **Componentes afetados:** `frontend/src/app/app/lancamentos/`, componentes de
  wizard, camada BFF e cliente tipado.
- **Dependencias:** IMP-306.
- **Criterios de conclusao:** campos tipados, sem JSON cru; nenhum UUID digitado
  pelo operador; nenhuma aritmetica no frontend; erro preserva o que foi
  digitado e exibe o correlation ID.
- **Suite minima:** unidade, componente, BFF e Playwright.
- **Status:** Concluido e **verificado em stack real** (Next.js + FastAPI +
  PostgreSQL); Playwright automatizado pendente, coberto pelo IMP-311.
- **Nota de execucao:** a busca de Devedor reusa a listagem existente em vez de
  criar uma consulta paralela. A navegacao ganhou `requiredAllPermissions`: o
  destino so aparece com as quatro permissoes da cadeia, porque exibir link que
  leva a "Sem permissao" e pior que nao exibir. Os diretorios da feature foram
  excluidos da varredura de foundation, como todas as demais features ja sao.
- **Defeitos encontrados apenas na verificacao manual**, nenhum detectado por
  unidade, componente, BFF ou contrato:
  1. `data_referencia` sem valor no formulario caia no proprio vencimento,
     gerando periodo de duracao zero — o Motor recusava com `data_fim deve ser
     posterior a data_inicio`. Os testes sempre enviavam o campo, entao o
     caminho real nunca era executado. Corrigido para a data do servidor, com
     regressao provada nos dois sentidos.
  2. CPF invalido atravessava os tres passos e voltava como erro generico. O
     backend explicava o digito verificador; a tela engolia. Rotulo passou a
     "CPF", com exemplo e validacao no passo 1.
  3. `401` de contexto nao era capturado na pagina. O layout guarda a propria
     chamada, mas layout e page renderizam concorrentemente e a rejeicao da
     pagina escapava como erro de Server Component. Mesma exposicao existe nas
     demais paginas e fica registrada como divida.
- **Guardrail respeitado:** a validacao de CPF usa laco explicito porque o
  scanner anti-motor-paralelo veta acumulador funcional e nao distingue digito
  verificador de soma financeira. A regra e cega por desenho; abrir excecao nela
  seria repetir o erro da DR-002.

### IMP-309 - Tela de emprestimos

- **Objetivo:** apresentar em andamento, quitados e encerrados a partir do
  estado oficial retornado pelo backend.
- **Componentes afetados:** `frontend/src/app/app/motor/`, componentes de
  listagem.
- **Dependencias:** nenhuma.
- **Criterios de conclusao:** nenhuma classificacao calculada no frontend;
  estados vazios explicitos.
- **Suite minima:** componente e Playwright.
- **Status:** Concluido.
- **Nota de execucao:** o agrupamento compara `loan.estado` literalmente com o
  estado que o backend devolve (`ativo`/`quitado`/`cancelado`); nao ha derivacao
  por data ou por saldo. Cada grupo declara a propria ausencia, em vez de uma
  unica mensagem para a pagina inteira. O nome do Devedor substitui o UUID como
  titulo da linha e e resolvido no servidor com **uma** chamada para a pagina
  toda, nunca uma por emprestimo; sem `devedor.ler` o rotulo degrada para
  "Devedor nao identificado" e a lista de emprestimos continua intacta.
- **Nota de gate:** as duas evidencias visuais da lista foram repinadas porque a
  tela mudou, e verificadas estaveis em quatro execucoes. As duas evidencias de
  **detalhe** foram encontradas nao deterministicas — variam entre execucoes
  identicas sem alteracao de codigo. Defeito anterior a este IMP, com medicao e
  consequencia registradas no relatorio do IMP-294.

### IMP-310 - Devedor com situacao do emprestimo

- **Objetivo:** o detalhe do Devedor passa a exibir os emprestimos dele.
- **Componentes afetados:** `frontend/src/app/app/devedores/[devedorId]/`.
- **Dependencias:** IMP-309.
- **Criterios de conclusao:** somente leitura; somente valores retornados.
- **Suite minima:** componente e Playwright.
- **Status:** Concluido.
- **Nota de execucao:** o bloco reusa o filtro `devedor_id` que a listagem de
  Emprestimos ja aceita — nenhuma superficie nova. Grupos vazios sao omitidos na
  pagina de um Devedor especifico, e a ausencia total tem mensagem propria.
- **Guardrail respeitado:** o gate de Devedores proibe **vocabulario**
  financeiro (`emprestimo`, `parcela`, `saldo`) em `components/devedores/`,
  `lib/bff/devedores.server.ts` e `lib/devedores/devedores-policy.ts`. Em vez de
  afrouxar a regra ou de contorna-la criando arquivo irmao nao varrido — que
  seria repetir a evasao documentada em `dependencies.py:643` —, a apresentacao
  de Emprestimo ficou em `components/motor/`, que ja e governado para isso, e a
  pagina do Devedor apenas a embute. O gate segue valendo integralmente.

---

# 4. Fase C - Certificacao

### IMP-311 - Jornada real e recertificacao

- **Objetivo:** cenario que preenche o wizard na interface contra FastAPI e
  PostgreSQL reais, ate o plano de parcelas.
- **Componentes afetados:** `frontend/tests/jornadas-e2e/`, matriz de
  rastreabilidade, relatorio do ciclo.
- **Dependencias:** IMP-308, IMP-309, IMP-310.
- **Criterios de conclusao:** o cenario falha se a cadeia quebrar em qualquer
  ponto, verificado nos dois sentidos; gates completos verdes; matriz sem
  declarar jornada observada que nao se completa.
- **Suite minima:** gates completos do PLAN-027.
- **Status:** Concluido em 2026-08-20.
- **Enunciado reescrito antes de executado.** O objetivo original terminava
  "ate o plano de parcelas", objeto que o IMP-327 removeu. Executar como estava
  certificaria uma tela que nao existe. O cenario passou a ser: **lancar pelo
  wizard, abrir o painel e receber um pagamento** — emprestimo livre, ponta a
  ponta, pela interface.
- **A jornada estava quebrada, e ninguem sabia.** Ela nao roda desde o IMP-327.
  A primeira execucao devolveu **4 de 8 cenarios vermelhos**, nenhum por causa
  do codigo novo:
  1. o seed chamava `POST /credit/emprestimos/{id}/parcelas` e mandava
     `quantidade_parcelas`, removidos no IMP-327;
  2. o cenario de RBAC esperava a palavra `denied`, que o PLAN-029 trocou por
     "Voce nao possui permissao para esta acao.";
  3. o painel do emprestimo era localizado pelo UUID no titulo, que o IMP-320
     trocou pelo nome de quem deve;
  4. o cenario do Motor esperava "Saldo oficial" e "Memoria de calculo
     oficial", que o IMP-326 trocou por "Deve hoje" e "Como a conta foi feita".
- **Seed no modelo novo:** `financial_parameters()` deixou de mandar
  `quantidade_parcelas` e `primeiro_vencimento` e passou a mandar
  `dia_de_acerto`, que chega ao Emprestimo pelos parametros do Contrato. O
  pagamento do seed virou R$ 500,00 na data de hoje, sem parcela a liquidar.
- **Verificado nos dois sentidos.** Com o saldo esperado trocado de
  R$ 1.500,00 para R$ 1.400,00, o cenario falha; com o valor certo, passa. O
  teste nao e vazio.
- **Uma assertiva que teria mentido:** a confirmacao do pagamento estava no
  texto `sr-only` do formulario, que **esta sempre na pagina**. Passaria com o
  pagamento recusado. Trocada pelo paragrafo de status de sucesso.
- **Achado que nao virou correcao — ambiguidade no valor digitado.** O campo do
  wizard aceita `2000,00` e `2000.00`, e recusa `2.000,00`. Mas aceita
  `2.000`, que o backend le como **dois reais**: quem digitar o separador de
  milhar sem os centavos leva um emprestimo mil vezes menor, sem aviso. Nao
  corrigido aqui porque escolher a interpretacao e decisao de produto, nao de
  teste. Ver §IMP-312-A proposto no handoff.
- **Resultado:** 8 de 8 cenarios verdes contra Next.js, FastAPI e PostgreSQL 16
  reais, incluindo login/RBAC/404 neutro, Devedor-Proposta-Contrato-Emprestimo,
  wizard-extrato-pagamento, cobranca/agenda/comunicacao, relatorios,
  configuracoes, IAM, automacao e 5xx correlacionado.

---

# 5. Gates

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate` com 0 erros e sem avisos novos;
- `npm run docs:test`;
- `node scripts/tests/test-plan-025-contracts.js`;
- `git diff --check`;
- frontend: typecheck, lint, unit, component, contract, BFF e build;
- Playwright de jornada real contra stack real;
- nenhum calculo financeiro fora do Motor e nenhum token no browser.

---

# 6. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.6.0 | 2026-08-20 | IMP-311 concluido: jornada real reescrita para o emprestimo livre e verde em 8/8 contra stack real. A execucao revelou que a suite estava quebrada desde o IMP-327 e desatualizada pelo PLAN-029. |
| 1.5.0 | 2026-08-17 | IMP-310 concluido: Devedor abre com os emprestimos dele; causa da evidencia visual irreprodutivel isolada e corrigida. |
| 1.4.0 | 2026-08-17 | IMP-309 concluido: lista em tres grupos pelo estado oficial, Devedor pelo nome e evidencia visual repinada. |
| 1.3.0 | 2026-08-17 | IMP-308 concluido em unidade, componente, BFF e contrato; verificacao em stack real pendente. |
| 1.2.0 | 2026-08-16 | IMP-306 concluido: endpoint de lancamento publicado, inventario em 108/137 e pinos de contrato avancados. |
| 1.1.0 | 2026-08-16 | IMP-305 concluido: lancamento composto em transacao unica, com a etapa financeira injetada para respeitar o guardrail de exclusividade do Motor. |
| 1.0.0 | 2026-08-16 | Backlog inicial IMP-305..IMP-311. |
