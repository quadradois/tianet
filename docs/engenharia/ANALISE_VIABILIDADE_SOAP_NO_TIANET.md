# Análise de viabilidade — SOAP aplicado ao TiaNet

**Status:** Analisado, decidido e **exercitado nas duas politicas de mutacao** — **v1.4.0**; o bloqueio da §11.1 foi resolvido por decisão do proprietário
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
| Fixar SHA de evidência nos relatórios (**transcrição**) | Média (44 pendentes hoje) | `test:certification` | **Executor barato** — mecânico e verificável |
| Regerar as evidências (**captura**) | Média | Só pela própria suíte, ~12 min | **Coordenador** — o custo é de máquina, não de modelo (§11.2) |
| Auditoria somente-leitura (ex.: campo `connected`) | Média | Inspeção do coordenador | **Executor barato**, retorno estruturado |
| Teste de unidade a partir de critério escrito | Alta (31% da churn) | `pytest`, segundos | **Executor barato**, com mutação obrigatória (§8) |
| Implementação de IMP com fronteira declarada | Alta | Gate completo | **Coordenador ou executor forte** |
| Concorrência, atomicidade, transação, lock | Baixa, alto risco | Humana + revisor especialista | **Revisor especialista** (§6) |
| Decisão de desenho, ADR, contrato de API | Baixa, irreversível | Porta humana | **Coordenador propõe, fundador decide** |

**Nota sobre o IMP-370, próximo da fila:** é péssimo primeiro candidato a
delegação. Ele carrega uma decisão de desenho não resolvida (o canal recebe o
token no construtor, e o worker monta um canal só na subida) e mexe em estado
que a tela lê. É trabalho de coordenador, não de executor barato.

**Bom primeiro candidato:** as 44 evidências desatualizadas pelo selo do IMP-369
— **mas só a metade certa delas**, e não com o rollback que escrevi aqui. A §11.2
divide a tarefa em captura e transcrição, e a §11.3 corrige o "reverter é `git
checkout`".

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

## 11. Emenda — o que as respostas do fundador mudaram (2026-09-04)

As cinco perguntas da §9 foram respondidas. Três respostas confirmam o desenho,
uma o corrige, e uma **abre um bloqueio que não existia na v1.0.0**.

### 11.1 — BLOQUEIO: o tier gratuito do revisor é incompatível com o papel dele

A §6 propôs convocar o revisor especialista por gatilho de risco, e listou os
gatilhos: UoW e lock, repositórios e migração, temporizador e estado
compartilhado, **autenticação, permissão e cifra**.

A política de dados informada diz que o Nemotron gratuito **registra sessões para
segurança e melhoria, e não deve receber conteúdo pessoal ou confidencial**. Os
modelos Muse Contributor permitem uso de prompt e resposta para treinamento
futuro.

**Os dois enunciados não podem valer ao mesmo tempo.** Os gatilhos que justificam
convocar o revisor são exatamente os que mandam para ele os arquivos que a
política exclui:

- `src/emprestimo/infrastructure/cifra.py` — a cifra do token da instância;
- `src/emprestimo/application/credenciais.py`;
- `src/emprestimo/domain/credit/devedor.py` e vizinhos — CPF como Value Object,
  com o caveat 3.4 ainda aberto sobre CPFs em `audit_log`;
- `src/emprestimo/application/autorizacao.py` e o desenho de permissões.

Não é objeção ao modelo nem ao conceito. É uma **incompatibilidade entre o tier e
o papel**, e ela tem três saídas honestas:

1. **Tier pago com retenção zero** para o papel de revisor. O revisor é o papel
   com melhor relação valor/custo do fluxo — ele lê muito e escreve nada —, e é o
   pior lugar para economizar com dado de terceiro;
2. **Revisor gratuito com escopo amputado**: só recebe diff que não toque cifra,
   credencial, permissão nem dado pessoal. Isso remove justamente os gatilhos de
   maior risco, e o que sobra é concorrência em código de apresentação;
3. **Aceitar o risco explicitamente**, por decisão registrada do proprietário,
   sabendo que o código do produto pode ser usado para treinamento.

**Recomendação:** opção 1 para o revisor, opção 2 para os executores de tarefa
mecânica — que não precisam ver esses arquivos para trocar SHA em relatório.

#### DECISÃO — 2026-09-04, fundador: `ACCEPTED_RISK`, opção 3

O proprietário escolheu a **opção 3** e o bloqueio está **resolvido**. O registro,
para que a decisão signifique a mesma coisa daqui a seis meses:

**O que foi aceito.** Que o código do produto — incluindo o desenho de cifra, de
autorização e de tratamento de CPF — possa ser registrado pelo provedor e usado
para melhoria ou treinamento do modelo. Palavras do fundador: *"estou ciente e
aceito tranquilamente"*.

**O que continua proibido, e não por cautela do executor e sim por política já
escrita:** segredo, token, credencial, **dado pessoal real**, conversa ou mídia
de cliente, e conteúdo de produção. Os testes deste repositório usam dados
sintéticos, e é isso que sustenta a frase *"não vamos trabalhar no
desenvolvimento com dados PII"*.

**A distinção que o registro precisa preservar:** dado pessoal real não trafega;
o **desenho** de como esse dado é tratado, sim. São coisas diferentes, e é a
segunda que a decisão aceita.

**Quando reabrir:** se o repositório passar a conter dado real (fixture com CPF
de cliente, dump, log de produção), ou se o produto ganhar cliente com cláusula
contratual de confidencialidade sobre o código. Aí a decisão volta à mesa — não
por mudança de política do provedor, mas por mudança do que temos a perder.

O SOAP §16 já exige isso ao dizer que segredo não entra em contrato. A emenda
apenas registra que **"conteúdo confidencial" aqui é mais amplo que segredo**:
inclui o desenho de autorização e o tratamento de dado pessoal.

### 11.2 — O piloto das 44 evidências estava mal decomposto (por mim)

Eu propus a tarefa inteira como uma unidade. Aplicando o critério da §4 ao pé da
letra, ela é **duas** tarefas com custos opostos:

| Etapa | Natureza | Custo | Quem faz |
|---|---|---|---|
| **Captura** — rodar as suítes Playwright que regeram os PNGs | Pesada e frágil ao ambiente: ~12 min, e hoje morreu por memória três vezes | Alto, e não cai com modelo barato | **Coordenador**, uma vez |
| **Transcrição** — calcular o SHA de cada PNG e fixá-lo no relatório certo | Mecânica, regra única, verificação instantânea | Baixo | **Executor barato** |

Delegar a captura não economiza nada: o custo dela é de máquina e de relógio, não
de modelo. Delegar a transcrição economiza exatamente o tipo de trabalho que o
conceito busca.

**Consequência para o piloto:** o lote de 5 vira lote de 5 **transcrições**, com
os PNGs já regerados e o baseline capturado. O executor recebe a lista de
arquivos, os SHAs calculados, o relatório de destino de cada um, e a proibição de
tocar em qualquer outra linha. Verificação: `npm run test:certification`.

Isso também torna o critério de sucesso mais honesto — ele mede transcrição fiel,
que é o que se quer medir, e não a capacidade de sobreviver a uma suíte Playwright
que derrubou a minha própria sessão três vezes.

### 11.3 — A ressalva sobre rollback está certa, e eu tenho o quase-incidente

Eu escrevi "rollback é `git checkout`". A ressalva de que isso só é seguro em
worktree dedicada com baseline limpo comprovado está correta, e hoje mesmo houve
o caso: **rodei `git checkout -- docs/audits/evidence/` três vezes** para limpar
PNGs que um gate interrompido tinha regerado na árvore compartilhada.

Funcionou porque as alterações eram todas do gate. Se houvesse trabalho humano
não commitado ali, eu o teria apagado sem aviso — e o SOAP §21 lista "limpar o
working tree para esconder conflito" como antipadrão, com razão.

**Adotado:** tarefa delegada roda em worktree dedicada, com baseline capturado
antes, e a reversão atinge só o que é atribuível ao executor.

### 11.4 — O que as outras respostas confirmam

**Revisor `READ_ONLY` que pode rodar diagnóstico** é o desenho certo, e resolve a
dúvida da §6: ele executa o que não muta e relata; a verificação material continua
sendo do coordenador. É o arranjo que fez o review do IMP-371 valer.

**Executor com comando permitido por contrato**, com a ressalva honesta de que a
proteção é contratual e não é sandbox — ela não vê escrita em `node_modules`,
cache ou `.venv`. Combinado com a §11.3, reforça worktree ou container para
qualquer tarefa que instale dependência ou rode E2E.

**O arnês está provado e o provedor não.** 36 testes e 304 verificações cobrem
contrato, classificação, restrição de caminho, preservação de baseline,
diferenciação entre falha de provedor e reprovação, e telemetria sanitizada.
Nada disso prova que um modelo responde. A taxa de 0/1 não mede qualidade: mede
que a única chamada morreu no provedor.

**O próximo passo é barato e decisivo:** repetir o smoke com o identificador do
catálogo. Isso foi **verificado na máquina em 2026-09-04**, e não é mais palpite:

`opencode models` devolve `opencode/muse-spark-1.3-contributor-free`. O
identificador usado no smoke, `opencode/muse-spark-1.3`, **não existe** na lista.
Os dois modelos que interessam ao desenho estão lá:
`opencode/nemotron-3-ultra-free` para o papel de revisor, e os
`muse-spark-*-contributor-free` para execução mecânica.

**Mas há uma segunda causa provável, e ela não se resolve corrigindo o
identificador.** `opencode auth list` mostra três credenciais — GitHub Copilot,
um provider próprio, e **OpenCode Go** — e **nenhuma para o OpenCode Zen**, que é
o namespace `opencode/*`. Aparecer em `opencode models` é catálogo; responder
exige credencial, exatamente como a §1 das respostas do fundador já dizia.

Ou seja: o `PROVIDER_ERROR` tem dois suspeitos, e o segundo é mais provável que o
primeiro. O teste que separa os dois é uma chamada mínima com o identificador
correto — se falhar de novo, o problema é autenticação, não nome.

### 11.6 — Não existe integração com o OpenCode neste repositório

Verificado em 2026-09-04. O CLI **está instalado na máquina** (1.18.27, com
config global própria), mas o repositório não tem nenhuma ligação com ele:

- nenhum script, adaptador, envelope ou telemetria em `scripts/` ou na raiz;
- a única ocorrência da palavra "opencode" em arquivo versionado é uma **lista
  consultiva de integrações compatíveis** dentro de `.specify/workflows/`, que é
  workflow de terceiro e não configura nada;
- o spec-kit deste repositório foi inicializado com a integração `claude`, e é a
  única em `.specify/integrations/`.

**O arnês descrito nas respostas do fundador — 36 testes, 304 verificações,
envelope v1/v2, telemetria sanitizada — vive no outro projeto, não aqui.**

Isso muda a pergunta operacional. Não é "como ligamos o OpenCode ao fluxo", é
**"portamos o arnês que já funciona, ou construímos um segundo?"**. A resposta
depende de a que ele está acoplado no outro projeto: layout de repositório,
linguagem, nome de gate, formato de contrato. Portar um arnês provado é sempre
mais barato que reescrever — e reescrever produziria um segundo lugar onde a
mesma regra pode divergir, que é o problema que o SOAP existe para evitar.

### 11.7 — Primeira delegação real, medida (2026-09-04)

O arnês do outro projeto foi descartado por decisão do fundador, e o cerimonial
do SOAP com ele. O que sobrou é o que basta: **uma invocação de linha de comando
dentro de uma worktree, verificada pelos gates que já existem.**

#### O mecanismo, inteiro

```
opencode run --pure --dir <worktree> -m <provider/modelo> "<contrato inline>"
```

Não falta framework. O CLI já traz `--dir` (aponta a worktree), `-m` (escolhe o
modelo), `--format json` (retorno estruturado) e `--pure` (sem plugins). A
fronteira é a worktree; a verificação é `git status` mais o gate da vez.

**Armadilha encontrada:** `-f` é flag de array e **engole a mensagem posicional**
— a primeira tentativa morreu com `File not found:` seguido do texto do prompt.
Contrato vai **inline**, não anexado.

#### Acesso: comprovado, 2/2

O `PROVIDER_ERROR` do smoke anterior era **o identificador**, e não a
credencial. Com o nome do catálogo, os dois modelos do desenho responderam:

| Modelo | Papel pretendido | Resultado |
|---|---|---|
| `opencode/muse-spark-1.3-contributor-free` | executor mecânico | respondeu |
| `opencode/nemotron-3-ultra-free` | revisor especialista | respondeu |

#### Tarefa real — auditoria do campo `connected`

Escolhida por ser somente-leitura (risco zero de mutação), por fechar um caveat
aberto, e por ter verificação barata: eu leio o mesmo código.

**Contrato:** política `READ_ONLY`, seis caminhos de leitura declarados, formato
de retorno fixado, condição de parada explícita ("se precisar sair da fronteira,
pare e diga qual caminho faltou").

**Resultado mecânico:** worktree **limpa** ao fim — a política `READ_ONLY` foi
cumprida sem precisar de sandbox. Retorno em português, no formato pedido, com
arquivo e linha em cada item.

**Adjudicação: `APPROVED_WITH_CONCERNS`.** A conclusão está **certa** — verifiquei
de forma independente. Mas o caminho até ela estava incompleto, e a diferença
importa:

- ele concluiu *"nenhum ponto lê o `connected` minúsculo de `/instance/all` ou
  `/instance/get`"*, o que sugere que não tocamos esses endpoints;
- **nós tocamos os dois**: `buscar_instancia` chama `/instance/all`, e
  `jid_da_instancia` chama `/instance/info/:id`. Nenhum dos dois apareceu na
  lista de seis lugares que ele enumerou;
- a resposta certa é mais forte que a dele: chamamos os endpoints ambíguos e
  lemos deles apenas `name`, `id`, `token` e `jid`. O campo ambíguo nunca é lido.

Ele **concluiu por ausência**, onde a pergunta pedia **inspeção**. Deu certo
porque a ausência era real; teria falhado calado se houvesse uma leitura escondida
num terceiro arquivo.

#### O que isso ensina para o próximo contrato

**Peça enumeração, não veredito.** O contrato dizia "descubra se o nosso código
mistura os dois significados", e um veredito é fácil de acertar por sorte. Se
tivesse dito *"liste todas as chamadas a `/instance/all` e `/instance/info` e,
para cada uma, os campos lidos"*, a resposta seria verificável item a item — e a
lacuna teria aparecido sozinha.

É a mesma lição da §2 do handoff do IMP-371, agora do outro lado: **um resultado
verde que não prova nada é pior que resultado nenhum**, valendo tanto para teste
quanto para parecer de agente.

#### Números, honestamente

- acesso: **2/2**;
- tarefa real: **1/1 aceita na primeira tentativa**, com ressalva de completude;
- custo em token: **não informado** pelo CLI no formato padrão. `--format json`
  precisa ser testado antes de qualquer conta de economia;
- amostra: **um**. Não roteia nada ainda, e dizer o contrário seria inventar
  regra a partir de uma observação.

#### Um terceiro achado, sobre nós mesmos

O primeiro commit desta seção **foi reprovado pelo nosso próprio validador**: eu
havia batizado a tarefa com um identificador de namespace novo, e o
`docs:validate` o recusou porque o namespace não está no Registry (SPEC-002).
Esta frase também não pode citá-lo: o validador reprova a **menção**, e não
apenas o uso — o que está certo, porque é assim que um namespace nasce por
descuido.

Vale registrar porque é o argumento central da §4 acontecendo ao vivo: **a
governança deste repositório é forte o bastante para pegar erro de quem coordena,
não só de quem executa.** É isso que torna delegação segura aqui — e é por isso
que a verificação não pode ser afrouxada para caber mais delegação.

A correção foi tirar o identificador, não registrar um namespace novo para uma
tarefa avulsa.

### 11.8 — Segunda delegação: com escrita, e o fluxo fechou (2026-09-04)

A primeira delegação foi somente-leitura e não exercitou o que mais importa: a
**fronteira de escrita**. Esta exercitou, de ponta a ponta.

**Escopo escolhido para baratear o teste:** em vez das 44 evidências, só a suíte
de dashboard — 4 PNGs reais regerados em 22s, contra ~12 minutos. Mesmo teste da
fronteira, um onze avos do custo. O `require-build` reprovou a primeira tentativa
por build velho, o que é o guardrail funcionando.

#### O que foi delegado

Substituir quatro SHA-256 num relatório de auditoria. O coordenador calculou os
valores e localizou o arquivo de destino; o executor **só transcreveu** — a
separação da §4 do contrato, para que um valor errado diga de qual etapa veio.

Modelo: `opencode/muse-spark-1.3-contributor-free`, o barato, no papel de
executor mecânico.

#### Verificação, feita pelo coordenador

| Verificação | Resultado |
|---|---|
| Arquivos modificados na worktree | **1**, exatamente o permitido |
| `git diff --numstat` | `4 4` — inserções iguais a remoções, forma preservada |
| Os quatro valores antigos | **0 ocorrências** cada |
| Os quatro valores novos | **1 ocorrência** cada |
| `npm run test:certification` na árvore principal | **passou** |

**Aceite na primeira tentativa, sem ressalva.** É a primeira vez que isso
acontece nesta série.

#### O que isso mostra, e o que não mostra

**Mostra** que o mecanismo inteiro funciona: contrato inline, worktree com
baseline, fronteira de escrita respeitada sem sandbox, retorno estruturado, e
verificação por gate oficial. Nenhuma peça de arnês foi necessária.

**Não mostra** que o modelo é bom. Transcrição é a tarefa mais fácil que existe
neste repositório, escolhida de propósito para separar "o fluxo funciona" de "o
modelo acerta". Duas amostras não roteiam nada.

**O contrato desta vez pedia enumeração**, não veredito — a lição da §11.7. O
retorno veio com os quatro pares aplicados, um por um, e cada um era conferível
em um comando. Foi o que tornou a verificação barata.

#### Fim do exercício

Conforme a §0 do contrato, o exercício terminou com a árvore como começou: os 4
PNGs e o relatório foram revertidos, e a worktree removida. O que fica é esta
seção.

### 11.5 — Ordem revista

1. Comprovar acesso real. O identificador correto já está verificado (§11.4); o
   suspeito principal passou a ser **credencial do OpenCode Zen ausente**. Uma
   chamada mínima separa os dois. **É o único passo que não depende de mim**;
2. ~~Decidir o tier do revisor.~~ **Feito**: risco aceito pelo proprietário
   (§11.1), tier gratuito liberado para todos os papéis;
3. Coordenador captura as 44 evidências e o baseline;
4. Piloto de 5 **transcrições** em worktree dedicada, verificação por
   `test:certification`;
5. Decidir entre **portar o arnês do outro projeto** ou construir um aqui
   (§11.6) — hoje este repositório não tem nenhuma integração com o OpenCode;
6. Só então falar em taxa de aceite e roteamento.

**Atualização de 2026-09-04:** os passos 1 e 5 foram resolvidos no mesmo dia. O
acesso está comprovado (§11.7) e a decisão sobre portar o arnês caiu — o fundador
descartou o do outro projeto, e a §11.7 mostra que **nenhum arnês é necessário**
para começar. Restam a captura e o piloto de transcrição.

---

## 12. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.4.0 | 2026-09-04 | §11.8: segunda delegacao, agora COM ESCRITA, e o fluxo fechou de ponta a ponta — fronteira respeitada, `numstat` 4/4, os quatro valores antigos ausentes e os novos presentes uma vez cada, e o verificador oficial passou. Primeiro aceite sem ressalva da serie. O contrato desta vez pediu enumeracao em vez de veredito, que e a licao da §11.7, e foi o que tornou a verificacao barata. Registra tambem que isso prova o MECANISMO e nao a qualidade do modelo: transcricao e a tarefa mais facil que existe aqui, escolhida de proposito para separar as duas coisas. |
| 1.3.0 | 2026-09-04 | Sai do papel: §11.7 registra a primeira delegacao real. O `PROVIDER_ERROR` era o identificador, nao a credencial — os dois modelos respondem. A tarefa de auditoria rodou em worktree dedicada, respeitou `READ_ONLY` sem sandbox e fechou um caveat aberto. Adjudicada como aprovada COM RESSALVA: a conclusao estava certa, mas ele concluiu por ausencia onde a pergunta pedia inspecao, e nao enumerou as duas chamadas aos endpoints ambiguos. A licao entrou no metodo: pedir enumeracao verificavel item a item, nao veredito. Registra tambem que nenhum arnes e necessario — `opencode run --dir` mais worktree mais os gates que ja existem bastam. |
| 1.2.0 | 2026-09-04 | O bloqueio da §11.1 caiu por decisao do proprietario: risco aceito, opcao 3, com o escopo registrado — o que trafega e o DESENHO de cifra, autorizacao e tratamento de CPF, nao dado pessoal real, que continua proibido pela politica ja escrita. Fica registrado tambem quando a decisao deve voltar a mesa: repositorio com dado real, ou cliente com clausula de confidencialidade sobre o codigo. |
| 1.1.0 | 2026-09-04 | Emenda §11, depois das respostas do fundador. Abre um bloqueio que a v1.0.0 nao tinha como ver: o tier gratuito do revisor registra sessao e **nao deve receber conteudo confidencial**, e os gatilhos que justificam convoca-lo — cifra, credencial, permissao, dado pessoal — mandam para ele exatamente os arquivos que a politica exclui. Tier e papel sao incompativeis, e a saida e decisao do proprietario. Corrige tambem a decomposicao do piloto, que eu havia proposto como uma unidade quando sao duas com custos opostos: a captura e pesada e nao barateia com modelo, a transcricao e mecanica e barateia. E acata a ressalva sobre rollback, com o quase-incidente do proprio dia. |
| 1.0.0 | 2026-09-04 | Primeira análise. A medição mudou a conclusão: com documentação em 36% da churn, 74 `fix` contra 43 `feat` e três rodadas de review custando ~258 mil tokens contra uma rodada de implementação, o gargalo é verificação e não escrita — condição que o próprio SOAP §22 nomeia como gatilho de redesenho. Daí os dois ajustes centrais: rotear por custo de verificação e fazer o revisor especialista substituir rodada em vez de somar. |
