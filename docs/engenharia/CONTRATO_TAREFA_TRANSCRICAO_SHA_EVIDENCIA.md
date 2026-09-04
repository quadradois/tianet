# Contrato de tarefa — transcrição de SHA de evidência

**Status:** Molde vigente, com o piloto pendente de acesso comprovado ao executor
**Data:** 4 de setembro de 2026
**Implementa:** `SOAP_COORDENACAO_DE_EQUIPE_DE_IA.md` §6, e o Passo 1 da
`ANALISE_VIABILIDADE_SOAP_NO_TIANET.md` §7
**Classe:** `SMALL` por lote, `STANDARD` no conjunto

---

## 1. Por que este contrato existe

É o **primeiro contrato de tarefa real** deste repositório, e foi escolhido por
ser o caso mais fácil de julgar: regra única, resultado comparável byte a byte,
verificação em segundos e nenhuma decisão de arquitetura.

Ele mede **transcrição fiel**, e nada além disso. Um aceite aqui não autoriza
delegar implementação; autoriza delegar a próxima transcrição.

O que **não** está neste contrato, e por quê: a **captura** das evidências. Ela
custa ~12 minutos de suíte Playwright e é frágil ao ambiente — o custo é de
máquina e de relógio, não de modelo, e delegá-la não economiza nada
(`ANALISE...` §11.2). A captura é do coordenador.

---

## 2. Objetivo

Para cada PNG de evidência regerado pelo coordenador, **substituir no relatório
correspondente o SHA-256 antigo pelo SHA-256 vigente**, sem alterar mais nada.

O `test:certification` exige que o SHA vigente de **cada** PNG apareça em algum
relatório sob `docs/audits/reports/`. Um SHA errado ou ausente reprova o gate.

## 3. Não objetivos

- não regerar, abrir, converter ou otimizar imagem;
- não alterar dimensão, nome de arquivo ou estrutura de tabela;
- não reescrever texto do relatório, nem "melhorar" redação;
- não tocar em evidência fora do lote;
- não criar, remover ou renomear relatório;
- não atualizar histórico de versões (é do coordenador, e é onde a decisão mora).

---

## 4. Entrada fornecida ao executor

O coordenador entrega, por lote:

| Campo | Conteúdo |
|---|---|
| `arquivos` | caminho de cada PNG do lote |
| `sha_vigente` | SHA-256 já calculado pelo coordenador, por arquivo |
| `relatorio_destino` | o `.md` que hoje contém o SHA antigo daquele arquivo |
| `sha_antigo` | o valor exato a ser substituído |
| `baseline` | commit de referência da worktree |

**O executor não calcula o SHA.** Calcular e transcrever na mesma tarefa
esconderia o erro: se o valor sai errado, não se sabe se foi o cálculo ou a
cópia. O coordenador calcula; o executor transcreve; o verificador confere.

---

## 5. Fronteiras e política de mutação

**Política:** escrita delimitada.

**Caminhos permitidos:** exclusivamente os `docs/audits/reports/*.md` nomeados em
`relatorio_destino` para o lote.

**Caminhos proibidos, sem exceção:** `src/`, `frontend/src/`, `tests/`,
`migrations/`, `docs/audits/evidence/` (os PNGs são entrada, não saída), qualquer
outro `docs/`, e a raiz do repositório.

**Ambiente:** worktree dedicada, criada pelo coordenador, com baseline capturado
antes. A reversão atinge só o que é atribuível ao executor — nunca
`git checkout` na árvore compartilhada (`ANALISE...` §11.3).

---

## 6. Comandos permitidos

- `npm --prefix frontend run test:certification` — o verificador oficial;
- `git status --short` e `git diff` — inspeção;
- leitura de arquivo.

**Proibido:** `git add`, `git commit`, `git checkout`, `git restore`, `git stash`,
qualquer instalação de dependência, qualquer suíte Playwright, qualquer comando
que escreva fora dos caminhos permitidos.

---

## 7. Critério de aceite

Todos, sem negociação:

1. cada `sha_antigo` do lote substituído pelo `sha_vigente` correspondente, no
   relatório correspondente;
2. `npm --prefix frontend run test:certification` **passa**;
3. `git diff --numstat` mostra alteração **somente** nos relatórios do lote;
4. em cada relatório tocado, o número de linhas adicionadas é igual ao de
   removidas — transcrição não muda a forma do documento;
5. nenhum arquivo criado, removido ou renomeado;
6. nenhum commit, nenhum staging.

**Critério do piloto (lote de 5):** os seis acima **na primeira tentativa**, sem
correção. Uma correção não reprova o modelo — reprova o lote como evidência de
aceite na primeira tentativa, que é o número que interessa medir.

---

## 8. Retorno esperado do executor

Estruturado, conforme SOAP §12:

- arquivos tocados, com contagem de linhas alteradas;
- pares `(sha_antigo → sha_vigente)` efetivamente aplicados;
- resultado do `test:certification`, transcrito literalmente;
- o que **não** foi feito, e por quê;
- qualquer divergência encontrada — por exemplo, `sha_antigo` que aparece em mais
  de um relatório, ou que não aparece em nenhum;
- estado recomendado: `IN_REVIEW`, `CORRECTION` ou `BLOCKED`.

**Isso é relato, não evidência.** O coordenador reexecuta o verificador e lê o
diff antes de qualquer aceite (SOAP §11).

---

## 9. Condição de parada e escalonamento

O executor **para e devolve `BLOCKED`** se:

- um `sha_antigo` não for encontrado no relatório indicado;
- o mesmo SHA aparecer em mais de um lugar;
- o verificador reprovar por motivo que não seja o lote;
- qualquer ação exigir tocar caminho proibido.

**Não tenta consertar por conta própria.** Divergência de entrada é problema do
contrato, e contrato é do coordenador.

**Limite:** uma correção delimitada com o mesmo executor. Reincidência reduz o
lote, troca a capacidade ou bloqueia (SOAP §10.2).

---

## 10. Telemetria da execução

Sem conteúdo, conforme SOAP §15. Registrar apenas: identificador do lote, modelo
efetivo, duração, resultado técnico, resultado do review, número de arquivos,
linhas alteradas, e motivo padronizado quando houver correção ou bloqueio.

**Não registrar:** prompt, resposta, trecho de código, SHA, nome de arquivo.

---

## 11. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-04 | Primeiro contrato de tarefa real do repositório. Separa cálculo de transcrição de propósito — juntos, esconderiam de qual dos dois veio o erro. Exclui a captura das evidências, que é do coordenador porque seu custo é de máquina e não de modelo. |
