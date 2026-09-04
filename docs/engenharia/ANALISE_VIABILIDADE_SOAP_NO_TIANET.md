# Análise de viabilidade — SOAP aplicado ao TiaNet

**Status:** Análise para decisão do fundador
**Data:** 4 de setembro de 2026
**Analisa:** `SOAP_COORDENACAO_DE_EQUIPE_DE_IA.md`
**Responsabilidade:** dizer se o conceito se aplica aqui, onde ele paga, onde ele custa, e o que precisa ser verificado antes de decidir

---

## 1. Veredito

**Viável, e por um motivo melhor que economia de token: este repositório já tem
a parte cara do SOAP construída.** O que falta é pequeno e é justamente a parte
barata.

Mas a economia esperada **não vem de onde parece**. A medição abaixo mostra que
o gargalo do TiaNet não é escrever código — é **verificar**. Um executor mais
barato ataca a menor das três fatias. Um revisor a mais, mal posicionado,
**aumenta** o custo em vez de reduzir.

A recomendação está na §10. Ela não é "sim" nem "não": é **sim com um critério
de roteamento diferente do que o SOAP sugere por padrão**.

---

## 2. O que este repositório já tem — e não deve reconstruir

O SOAP §5 lista oito conceitos estáveis. Sete já existem aqui, com outro nome:

| Conceito do SOAP | Como já existe no TiaNet | Maturidade |
|---|---|---|
| Autoridade coordenadora | `ARCHITECTURAL-SUCCESSION-ROLE.md` | Escrita e vigente |
| Contrato de tarefa explícito | IMPs do Execution Backlog, com objetivo, escopo, critério de pronto e "fica de fora" | **Forte** — o IMP-371 tem os cinco campos |
| Execução delimitada | ALP-001 §3: blocos de ~5 IMPs por Gate | Escrita, pouco exercitada |
| Revisão independente | Rodadas do Codex antes do PR | **Forte na prática, não escrita** |
| Tentativas limitadas | Não existe | **Ausente** |
| Evidência antes de conclusão | `hooks/pre-push`, `test:certification` com SHA fixado, snapshot OpenAPI, guardrail de Client Components, `docs:validate` | **Muito forte** |
| Telemetria sem conteúdo | Não existe | **Ausente** |
| Fonte de verdade persistente | `docs/`, handoff versionado com ponteiro de máquina | **Muito forte** |

As portas do SOAP §11 também já existem: FOUNDATION, PLAN, Execution Backlog,
GATE-E, ADR e DR cobrem de "problema compreendido" até "handoff recuperável".

**Consequência para a decisão:** adotar o SOAP aqui não é implantar um sistema
novo. É **nomear o que já operamos** e acrescentar três peças: contrato de tarefa
em formato que uma máquina leia, limite de tentativas, e telemetria. O SOAP §19
chamaria isso de sair do Nível 1 para o Nível 2.

**O que NÃO deve ser reconstruído:** o sistema de evidências. Ele é o ativo mais
valioso do repositório para esta ideia — e a §4 explica por quê.

---

## 3. Onde o custo realmente está (medido, não estimado)

### 3.1 — O trabalho deste repositório, por classe

Últimos 60 commits, linhas alteradas:

| Classe | Linhas | Fatia |
|---|---:|---:|
| Documentação | 3.579 | ~36% |
| Código | 3.079 | ~31% |
| Testes | 3.071 | ~31% |

Últimos ~220 commits, por tipo: **74 `fix`, 58 `docs`, 43 `feat`**.

Duas leituras diretas:

1. **Mais de um terço do trabalho é documentação**, e documentação aqui tem
   validador que roda em segundos (`docs:validate`, 372 verificações);
2. **Corrigimos quase o dobro do que criamos** (74 `fix` contra 43 `feat`). Isso
   é sintoma de que o esforço está na convergência, não na primeira escrita.

### 3.2 — O custo do ciclo do IMP-371, observado hoje

O IMP-371 é uma amostra pequena, mas é a única com número real:

| Etapa | Custo observado |
|---|---|
| Implementação inicial (3 consertos) | 1 rodada minha |
| Review adversarial | **3 rodadas**, ~258 mil tokens só nos agentes de review |
| Achados | 24 do review + 3 do gate |
| Gate de pre-push | ~12 min por execução, **5 execuções** até passar |
| Correções | 3 commits de conserto, cada um exigindo o gate de novo |

**A implementação foi a parte barata.** Três rodadas de review e cinco execuções
de gate dominaram o custo — e as duas últimas execuções falharam por ambiente
(memória, porta presa, sonda de Postgres errada), não por defeito de código.

### 3.3 — A conclusão desconfortável

O SOAP §22 lista as condições que pedem redesenho. Uma delas é:

> "o review se tornar gargalo maior que a execução"

**Nós já estamos nessa condição.** Ela não é hipótese futura — é o retrato de
hoje. Isso muda o desenho: acrescentar um revisor ao fim da fila piora o
gargalo. O revisor novo precisa **substituir rodada**, não somar.

---

## 4. O critério de roteamento que proponho

O SOAP §5 lista as dimensões de seleção de capacidade: análise, raciocínio
arquitetural, precisão mecânica, contexto longo, custo. São dimensões do
**executor**.

Proponho uma dimensão a mais, e ela deveria ser a primeira aqui: **o custo de
verificar o resultado**.

```
Roteie pelo custo de VERIFICAÇÃO, não pela dificuldade da tarefa.
```

O motivo é aritmético. Se um executor barato erra e precisa de duas voltas, o
custo real não é o token dele — é o meu tempo de review mais o gate. Com gate de
12 minutos, duas voltas a mais custam mais que a economia de qualquer modelo.

Isso divide o trabalho do TiaNet em duas famílias:

**Verificação barata e determinística (segundos):**
- documentação → `docs:validate` (372 checks, ~9s no CI);
- SHAs de evidência → `test:certification` (instantâneo);
- contrato de API → `api:check` contra snapshot governado;
- domínio puro → `pytest tests/unit/domain` (segundos);
- lint, `mypy`, `black`, guardrail de Client Components.

**Verificação cara (minutos, ou humana):**
- qualquer coisa que exija Playwright (12 min de gate);
- concorrência, atomicidade e ordem de efeitos;
- decisão de desenho, contrato de API novo, migração;
- qualquer coisa cujo defeito seja "o comentário promete o que o código não faz"
   — que é o defeito recorrente deste projeto, e nenhum linter pega.

**Regra:** executor barato só recebe tarefa da primeira família. Não porque é
incapaz da segunda, mas porque na segunda a verificação come a economia.

---

## 5. Classes de tarefa do TiaNet, roteadas

| Classe | Frequência | Verificação | Roteamento proposto |
|---|---|---|---|
| Atualizar doc de governança, handoff, backlog | Alta (36% da churn) | `docs:validate`, segundos | **Executor barato**, com o coordenador revisando sentido |
| Regenerar evidências e fixar SHA nos relatórios | Média (44 PNGs pendentes hoje) | `test:certification` | **Executor barato** — mecânico e verificável |
| Auditoria somente-leitura (ex.: campo `connected`) | Média | Inspeção do coordenador | **Executor barato**, retorno estruturado |
| Teste de unidade a partir de critério escrito | Alta (31% da churn) | `pytest`, segundos | **Executor barato**, com mutação obrigatória (§8) |
| Implementação de IMP com fronteira declarada | Alta | Gate completo | **Coordenador ou executor forte** |
| Concorrência, atomicidade, transação, lock | Baixa, alto risco | Humana + revisor especialista | **Revisor especialista** (§6) |
| Decisão de desenho, ADR, contrato de API | Baixa, irreversível | Porta humana | **Coordenador propõe, fundador decide** |

**Nota sobre o IMP-370, próximo da fila:** é péssimo primeiro candidato a
delegação. Ele carrega uma decisão de desenho não resolvida (o canal recebe o
token no construtor, e o worker monta um canal só na subida) e mexe em estado
que a tela lê. É trabalho de coordenador, não de executor barato.

**Bom primeiro candidato:** as 44 evidências desatualizadas pelo selo do IMP-369.
Mecânico, volumoso, verificação instantânea, e reverter é `git checkout`.

---

## 6. O revisor especialista, sem virar quarta rodada

A proposta de trazer um modelo forte em concorrência e atomicidade tem lastro
neste repositório. Os achados difíceis de hoje foram todos dessa família:

- a serialização era da **aba**, não da instância;
- o advisory lock do `ConectarWhatsApp` **é liberado antes** das chamadas
  externas — existe um lock que parece cobrir mais do que cobre;
- os mapas de client do provedor não têm mutex, e a recomendação dele é estreita
  (`connect`/`logout`/`qr` sim, `status` não).

Nenhum desses veio de mim. O primeiro veio na **terceira** rodada.

**Onde ele entra sem somar custo:** não no fim da fila, e sim como **revisor
convocado por gatilho de risco** (SOAP §6.5), em paralelo com a revisão geral, na
**primeira** rodada. Gatilhos concretos para este repositório:

- o diff toca `application/` com UoW, lock, ou ordem de efeito externo;
- o diff toca `infrastructure/repositories/` ou migração;
- o diff toca temporizador, polling, retry ou estado compartilhado no frontend;
- o diff toca autenticação, permissão ou cifra.

Se o gatilho não dispara, ele não é chamado. O objetivo é **uma rodada com dois
revisores especializados** substituir **três rodadas com um revisor genérico**.

**O ponto de desenho que precisa ser decidido:** o que fez o Codex valer hoje não
foi o parecer — foi **poder rodar**. Ele leu o diff, executou os testes e apontou
que um deles passava pelo motivo errado; eu confirmei quebrando o código. Um
revisor que só lê produz alegações que alguém precisa verificar depois. Isso é
aceitável — foi assim que tratei o Codex de qualquer forma —, mas o custo de
verificação recai sobre o coordenador, e isso entra na conta da §4.

---

## 7. Adoção mínima viável, em ordem

Cada passo é útil sozinho e reversível. Nenhum exige o seguinte.

**Passo 1 — Contrato de tarefa legível por máquina.**
As IMPs já contêm o conteúdo. Falta o formato. Um bloco no início de cada IMP
com: fronteiras permitidas, política de mutação, critério de aceite e comando de
verificação. Sem isso, nada mais funciona; com isso, mesmo a delegação manual
melhora.

**Passo 2 — Um executor barato, numa classe só.**
Começar pelas evidências desatualizadas. Uma classe, verificação instantânea,
rollback trivial. Se sobreviver a três tarefas, ganha a segunda classe.

**Passo 3 — Limite de tentativas e telemetria mínima.**
O SOAP §10 e §15. Três campos bastam para começar: classe da tarefa, executor
efetivo, resultado do review. Sem conteúdo, como manda a §15.

**Passo 4 — Revisor especialista por gatilho.**
Só depois de 2 e 3, porque o gatilho depende de saber classificar o diff, e a
telemetria é o que diz se ele está substituindo rodada ou somando.

**Passo 5 — Roteamento assistido.**
SOAP Nível 4. Só com amostra suficiente. Antes disso, roteamento é o coordenador
escolhendo à mão, e está tudo bem.

---

## 8. Riscos específicos deste repositório

**O defeito recorrente daqui não é sintático, e nenhum gate pega.** "Comentário
que promete o que o código não faz" aconteceu quatro vezes documentadas: o
rollback que dizia cobrir cifra ausente, o usuário somente-leitura que não
existia, o polling que "só roda quando há o que esperar" e rodava sempre, e o meu
debounce que o teste não testava. **Modelo mais barato tende a produzir mais
comentário confiante**, porque comentário bonito é barato de gerar e caro de
verificar. Mitigação: comentário novo entra na lista de revisão do coordenador,
sempre.

**Teste que passa pelo motivo errado.** Foi a lição de hoje. Mitigação, já
adotada: quando um teste guarda uma condição booleana, remover a condição e ver o
teste falhar. É barato e é a única evidência de que o teste guarda algo. Deve
entrar no critério de aceite de toda tarefa de teste delegada.

**Português com o *porquê*.** Não é preferência estética: os comentários deste
repositório carregam a decisão e o incidente que a motivou. Um executor que
escreve comentário descritivo ("incrementa o contador") passa no lint e degrada o
ativo. Precisa estar no contrato, com exemplo.

**O gate é caro e frágil ao ambiente.** 12 minutos, e hoje falhou três vezes por
memória, porta presa e sonda errada. Delegar tarefas que exigem o gate completo
multiplica esse custo. Reforça a §4.

**Custo de coordenação não é zero.** Escrever contrato, revisar retorno e
reexecutar evidência consome tokens do coordenador. Em tarefa pequena, isso pode
custar mais que fazer. O SOAP §21 chama de "transformar toda tarefa simples em
cerimônia arquitetural". O limiar precisa ser observado, não presumido.

---

## 9. O que precisa ser verificado antes de decidir

Não tenho como responder isto sozinho, e são as perguntas que mudam a conta:

1. **Acesso e custo real** dos modelos pretendidos — via API, local, ou
   plataforma; preço por token de entrada e saída; limite de contexto. Este
   repositório manda diffs grandes com muito comentário: contexto curto elimina
   candidatos antes do preço.
2. **Política de dados** do provedor. O SOAP §16 proíbe segredo no contrato, mas
   o código do produto sai da máquina de qualquer jeito. Precisa ser decisão
   consciente, não descoberta depois.
3. **Se o revisor especialista pode executar** comandos, ou só lê. Muda o papel
   dele e o custo de verificação (§6).
4. **Se o executor barato roda com as ferramentas daqui** — `uv`, `npm`,
   Playwright, Docker — ou só edita arquivo. Se só edita, a verificação inteira
   volta para o coordenador, e a economia encolhe.
5. **O que já funciona no seu outro projeto**: qual classe de tarefa foi
   delegada, qual taxa de aceite na primeira tentativa, e o que precisou voltar.
   É a única evidência real disponível, e vale mais que qualquer benchmark.

---

## 10. Recomendação

**Adotar, com três ajustes ao conceito:**

1. **Rotear pelo custo de verificação**, não pela dificuldade da tarefa (§4).
   É o ajuste que mais muda o resultado neste repositório.
2. **O revisor especialista substitui rodada, não soma.** Convocado por gatilho
   de risco, em paralelo, na primeira rodada (§6). Se ele virar quarta opinião no
   fim da fila, piora exatamente o gargalo medido na §3.3.
3. **Começar pelo Passo 1 e 2 da §7**, e só avançar com evidência. O repositório
   já está no Nível 1 do SOAP com folga; o Nível 2 é uma tarde de trabalho, e o
   Nível 5 não deveria ser meta.

**Sobre o meu papel:** aceito o chapéu de coordenador, com uma ressalva honesta —
o coordenador do SOAP §11 tem uma obrigação que não pode ser delegada: *reexecutar
ou observar os checks materiais*. Isso significa que eu continuo rodando o gate e
lendo diff. O que muda é que eu paro de escrever a primeira versão de tudo, e
passo a escrever contrato, ler retorno e verificar. **A economia vem de eu
executar menos, não de eu verificar menos** — e se algum desenho futuro propuser
cortar a verificação do coordenador, é ali que o sistema quebra.

---

## 11. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-04 | Primeira análise. A medição mudou a conclusão: com documentação em 36% da churn, 74 `fix` contra 43 `feat` e três rodadas de review custando ~258 mil tokens contra uma rodada de implementação, o gargalo é verificação e não escrita — condição que o próprio SOAP §22 nomeia como gatilho de redesenho. Daí os dois ajustes centrais: rotear por custo de verificação e fazer o revisor especialista substituir rodada em vez de somar. |
