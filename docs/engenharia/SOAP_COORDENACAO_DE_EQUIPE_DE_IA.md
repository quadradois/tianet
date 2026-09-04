# SOAP — Coordenação de equipe de IA para trabalho de engenharia

**Status:** Referência reutilizável em revisão
**Data:** 4 de setembro de 2026
**Responsabilidade:** definir o conceito operacional; não prescrever plataforma, fornecedor, modelo ou ferramenta

## 1. Definição

Neste documento, **SOAP** significa **Standard Operating Automation Procedure**: um procedimento operacional padrão para coordenar uma equipe de executores de IA com supervisão, evidência e limites claros.

O SOAP descreve o que precisa acontecer para que uma demanda seja delegada, executada, revisada e concluída com segurança. Ele não determina qual produto atua como coordenador, qual ferramenta chama os modelos, qual LLM executa cada papel ou qual linguagem implementa a automação.

Uma adoção é compatível quando preserva os contratos, estados, autoridades e evidências definidos aqui, mesmo que sua tecnologia seja completamente diferente.

## 2. Problema resolvido

Sem um procedimento comum, equipes de IA tendem a operar como chats isolados:

- recebem contexto variável;
- interpretam escopo de maneiras diferentes;
- alteram áreas não autorizadas;
- confundem relato com evidência;
- repetem tentativas sem limite;
- perdem decisões entre sessões;
- deixam responsabilidade e aprovação ambíguas;
- otimizam velocidade local enquanto aumentam retrabalho global.

O SOAP transforma esse comportamento em um sistema coordenado no qual cada execução é uma unidade delimitada, observável, revisável e reversível.

## 3. Objetivo

Permitir que uma pessoa ou equipe coordenadora distribua trabalho entre agentes e modelos especializados, mantendo:

- uma única autoridade de coordenação;
- separação entre decidir, executar, revisar e aprovar;
- contexto mínimo suficiente;
- escopo e permissões explícitos;
- evidência observável para cada conclusão;
- correção limitada e consciente;
- continuidade entre sessões;
- telemetria útil sem capturar conteúdo sensível;
- independência de plataforma e fornecedor.

## 4. Escopo e não objetivos

### Incluído

- descoberta, arquitetura, planejamento, execução e verificação;
- tarefas de documentação, análise, código, testes e revisão;
- uso de um ou vários modelos com capacidades diferentes;
- trabalho sequencial ou paralelo com reconciliação central;
- falhas técnicas, falhas de provedor e reprovação de qualidade;
- handoff e aprendizado operacional.

### Não incluído

- autonomia irrestrita para publicação, produção, compra ou ações externas;
- aprovação automática de arquitetura, plano, risco ou release;
- confiança automática na resposta de um modelo;
- seleção de fornecedor por popularidade ou preferência pessoal;
- armazenamento de prompts, respostas, segredos ou dados pessoais como telemetria;
- obrigação de usar múltiplos agentes quando uma execução simples é suficiente.

## 5. Conceitos estáveis e configurações locais

| Conceito estável | Configuração que cada equipe pode escolher |
|---|---|
| uma autoridade coordenadora | pessoa, serviço ou agente que ocupa o papel |
| contrato de tarefa explícito | JSON, formulário, documento, ticket ou mensagem estruturada |
| execução delimitada | processo efêmero, sessão isolada ou job controlado |
| revisão independente | revisor humano, agente diferente ou combinação dos dois |
| tentativas limitadas | quantidade, intervalo, troca de modelo e critérios de parada |
| evidência antes de conclusão | suíte de testes, inspeção, medição, simulação ou aprovação humana |
| telemetria sem conteúdo | armazenamento, schema, retenção e ferramenta de análise |
| fonte de verdade persistente | repositório, sistema documental ou gerenciador de trabalho |

O que pode variar é a implementação. O que não pode variar silenciosamente é a responsabilidade de cada papel e o significado dos estados.

## 6. Papéis

### 6.1. Proprietário da decisão

Define objetivo, prioridades e limites de risco. Aprova decisões materiais, planos relevantes, exceções e riscos aceitos. Pode ser uma pessoa ou um colegiado claramente identificado.

### 6.2. Coordenador

É a autoridade operacional única do fluxo. Recupera contexto, classifica o trabalho, escolhe o processo proporcional, divide tarefas, seleciona capacidades, emite contratos, acompanha execuções, revisa resultados e mantém a fonte de verdade.

O coordenador pode ser assistido por IA, mas a função deve permanecer identificável e não pode ser disputada por executores concorrentes.

### 6.3. Executor

Realiza uma tarefa delimitada dentro do contrato recebido. Pode analisar, documentar, modificar ou testar conforme autorização. Não redefine escopo, não aprova seu próprio trabalho e não presume autoridade externa.

### 6.4. Revisor

Ataca a entrega por critérios de correção, segurança, escopo, evidência e regressão. Pode ser humano ou uma instância independente de IA. Seu parecer informa a decisão; não substitui o coordenador nem o proprietário.

### 6.5. Especialista

É convocado por gatilho de domínio ou risco — por exemplo segurança, arquitetura agentic, dados, privacidade ou infraestrutura. Produz análise especializada e achados classificados. Normalmente opera em somente leitura.

### 6.6. Sistema de evidências

É o conjunto de verificações capazes de observar se o resultado esperado ocorreu. Pode incluir testes, linters, inspeção de diferenças, simulações, métricas e revisão humana.

### 6.7. Fonte de verdade

Preserva requisitos, decisões, planos, estado e handoff. Conversa, memória de agente e saída bruta não substituem essa fonte.

## 7. Separação de autoridade

| Ação | Executor | Revisor/especialista | Coordenador | Proprietário |
|---|---:|---:|---:|---:|
| propor solução | Sim | Sim | Sim | Sim |
| alterar dentro do contrato | Quando autorizado | Normalmente não | Sim, se autorizado | Pode autorizar |
| ampliar escopo | Não | Não | Propõe | Aprova quando material |
| declarar checks executados | Sim, como relato | Sim, como relato | Reexecuta/observa | Não aplicável |
| aprovar o próprio trabalho | Não | Não | Não sem evidência | Decide portas materiais |
| fechar porta operacional | Não | Não | Sim, quando a governança permitir | Confirma portas reservadas |
| aceitar risco material | Não | Recomenda | Registra e recomenda | Sim |
| publicar ou atuar externamente | Não por padrão | Não | Somente com autorização | Autoriza explicitamente |

## 8. Fluxo as-is e to-be

### As-is típico: delegação informal

```text
Pedido → escolha intuitiva de modelo → prompt livre → resposta
                                      ↓
                         correção improvisada ou aceite
```

Nesse fluxo, contexto, autoridade, critérios e evidências permanecem implícitos.

### To-be: coordenação governada

```text
Demanda
   ↓
Recuperar verdade e baseline
   ↓
Classificar risco, impacto e workflow
   ↓
Arquitetura/decisão/plano necessários estão aprovados?
   ├─ não → analisar, decidir e planejar; parar na porta humana
   └─ sim
        ↓
Decompor em unidade verificável
        ↓
Emitir contrato de tarefa mínimo
        ↓
Selecionar capacidade adequada
        ↓
Executar em limite controlado
        ↓
Coletar resultado + diferença + checks relatados
        ↓
Revisar de forma independente
   ┌────┼───────────────┐
   ↓    ↓               ↓
Aceite  Correção        Bloqueio
   ↓    limitada           ↓
Reexecutar evidências   decisão, redução ou espera
   ↓
Atualizar verdade, telemetria e handoff
   ↓
Próxima unidade ou conclusão
```

## 9. Ciclo operacional detalhado

### Etapa 0 — Entrada e intenção

O coordenador registra:

- resultado desejado;
- motivo e valor;
- restrições explícitas;
- o que não deve acontecer;
- autoridade já concedida;
- necessidade de decisão humana.

Saída: demanda compreensível sem depender de contexto oral oculto.

### Etapa 1 — Recuperação de contexto

Antes de delegar, o coordenador consulta a fonte de verdade, instruções locais, decisões, estado atual, plano vigente, alterações preexistentes e evidências anteriores.

Saída: baseline conhecido e conflitos identificados.

### Etapa 2 — Classificação e triagem

A demanda é classificada pelo impacto real, não pelo tamanho do texto. Dimensões mínimas:

- reversibilidade;
- quantidade de fronteiras afetadas;
- dados e privacidade;
- segurança e autorização;
- dependências externas;
- efeitos mutáveis;
- arquitetura ou decisão aberta;
- impacto inteligente/agentic;
- custo de erro e de rollback.

Saída: workflow proporcional, especialistas necessários e portas aplicáveis.

### Etapa 3 — Prontidão para execução

O coordenador confirma se requisitos, arquitetura, decisão, plano, critérios de aceite e rollback estão suficientes para o risco. Se algo material estiver aberto, o fluxo permanece em análise e não cria tarefa de implementação.

Saída: autorização explícita para planejar ou executar, nunca presumida.

### Etapa 4 — Decomposição

O trabalho é dividido em unidades pequenas que entregam um resultado observável. Cada unidade deve poder ser aceita, corrigida, bloqueada ou revertida sem exigir que todo o projeto termine.

Boa unidade:

- possui um objetivo principal;
- altera fronteiras conhecidas;
- tem orçamento de mudança;
- possui checks proporcionais ao risco;
- produz evidência útil isoladamente.

Saída: fila de unidades ordenadas por dependência e risco.

### Etapa 5 — Seleção de capacidade

O coordenador escolhe o executor por adequação demonstrada à tarefa, considerando:

- análise e síntese;
- raciocínio arquitetural;
- precisão mecânica;
- programação e testes;
- contexto longo;
- multimodalidade;
- velocidade e custo;
- disponibilidade e política de dados;
- histórico de qualidade naquela classe.

O roteamento é hipótese revisável. Nenhum modelo recebe propriedade permanente de uma classe sem evidência suficiente.

Saída: executor primário e regra deliberada de fallback.

### Etapa 6 — Contrato da tarefa

O coordenador emite um envelope semântico contendo, no mínimo:

- identificador e número da tentativa;
- workflow e classificação;
- objetivo e não objetivos;
- referência da decisão/plano e unidade atual;
- baseline conhecido;
- fronteiras e caminhos permitidos;
- política de mutação: somente leitura ou escrita delimitada;
- critérios de aceite;
- verificações esperadas;
- ações permitidas e proibidas;
- classificação dos dados;
- formato de retorno;
- condição de parada e escalonamento.

O contrato contém somente o contexto necessário. Segredos e dados pessoais não são incluídos.

Saída: tarefa verificável antes de iniciar execução.

### Etapa 7 — Execução controlada

Cada execução possui identidade, início, fim e limite. O executor:

- confirma entendimento ou reporta ambiguidade material;
- atua somente dentro das permissões;
- preserva baseline preexistente;
- interrompe diante de conflito de escopo, segredo ou decisão ausente;
- executa os checks autorizados;
- retorna resultado estruturado.

Execução efêmera é o padrão conceitual porque reduz estado oculto. Sessões persistentes exigem justificativa, isolamento, expiração e recuperação próprios.

Saída: entrega candidata, nunca conclusão automática.

### Etapa 8 — Coleta e normalização

O coordenador coleta separadamente:

- resposta do executor;
- mudanças observadas;
- checks que o executor afirma ter feito;
- duração e estado técnico;
- falhas de ferramenta/provedor;
- desvios do contrato.

Uma falha externa não é igual a uma reprovação técnica. Uma resposta textual de sucesso não é igual a efeito comprovado.

Saída: pacote de revisão com fatos e relatos diferenciados.

### Etapa 9 — Review independente

O revisor examina:

- aderência ao objetivo;
- escopo e mutações;
- correção e completude;
- segurança, privacidade e autorização;
- regressões;
- testes enfraquecidos ou ausentes;
- alegações sem evidência;
- coerência documental;
- rollback.

Achados usam severidade clara, como:

- `BLOCKER`: impede avançar;
- `CONCERN`: risco real que exige resolução ou aceitação explícita;
- `SUGGESTION`: melhoria não bloqueadora;
- `APPROVED`: nenhum bloqueio material encontrado.

Saída: parecer de revisão, não adjudicação automática.

### Etapa 10 — Adjudicação e correção

Cada achado relevante recebe estado e responsável:

- `OPEN`;
- `RESOLVED` com evidência;
- `ACCEPTED_RISK` pela autoridade competente;
- `REJECTED_WITH_RATIONALE` com justificativa verificável.

Correções permanecem limitadas:

1. primeira correção pode permanecer com o mesmo executor se o problema for localizado;
2. reincidência exige reduzir a tarefa, trocar capacidade ou revisar o contrato;
3. repetição automática ilimitada é proibida;
4. decisão ausente, falha recorrente ou risco material encerra a tentativa como bloqueada.

Saída: nova candidata ou bloqueio honesto.

### Etapa 11 — Verificação pelo coordenador

O coordenador reexecuta ou observa os checks materiais e relaciona:

```text
Requisito → evidência esperada → check → resultado observado → status
```

Status recomendados:

- `VERIFIED`;
- `VERIFIED_WITH_CONCERNS`;
- `NOT_VERIFIED`;
- `BLOCKED`.

Saída: conclusão sustentada por observação independente.

### Etapa 12 — Persistência e continuidade

Após cada unidade significativa:

- atualizar estado e plano;
- registrar decisões e exceções materiais;
- preservar evidências duráveis;
- registrar riscos residuais;
- produzir handoff com próximo passo;
- gerar telemetria sanitizada.

A saída bruta de um modelo só entra na fonte de verdade depois de reconciliada e revisada.

Saída: outra equipe ou sessão consegue continuar sem redescobrir o trabalho.

## 10. Estados operacionais

| Estado | Significado | Próximas transições válidas |
|---|---|---|
| `DRAFTED` | demanda ainda sendo estruturada | `READY`, `BLOCKED` |
| `READY` | contrato e pré-condições completos | `RUNNING` |
| `RUNNING` | executor em atividade | `IN_REVIEW`, `BLOCKED` |
| `IN_REVIEW` | entrega candidata sob inspeção | `APPROVED`, `CORRECTION`, `BLOCKED` |
| `CORRECTION` | correção delimitada autorizada | `RUNNING`, `BLOCKED` |
| `APPROVED` | review e evidências suficientes para a unidade | próxima unidade ou verificação final |
| `BLOCKED` | avanço inseguro ou impossível | decisão, redução, mudança externa ou encerramento |

Estado técnico do processo e estado de qualidade da entrega são dimensões diferentes. Um processo pode terminar com sucesso técnico e produzir entrega reprovada; pode também falhar tecnicamente sem dizer nada sobre a qualidade da solução proposta.

## 11. Portas de governança

O nome e a quantidade de portas podem variar, mas o sistema precisa distinguir:

1. problema compreendido;
2. arquitetura suficiente;
3. decisão material aprovada;
4. plano executável aprovado;
5. unidade pronta;
6. execução concluída;
7. testes aprovados;
8. review adjudicado;
9. verificação concluída;
10. handoff recuperável.

Uma porta existe para impedir um tipo concreto de erro. Se não houver risco correspondente, o processo pode ser simplificado. Se houver risco, remover a porta por conveniência apenas oculta o problema.

## 12. Contrato de retorno do executor

O executor deve responder de forma estruturada com:

- resultado produzido;
- arquivos, recursos ou artefatos tocados;
- checks executados e seus resultados;
- checks não executados e motivo;
- desvios ou decisões encontrados;
- riscos e limitações;
- estado recomendado: review, correção ou bloqueio.

Esse retorno é relato do executor. O coordenador ainda precisa observar o estado real.

## 13. Concorrência e paralelismo

Paralelizar somente unidades independentes. Antes do fanout, declarar ownership de arquivos, módulos, dados ou decisões. O coordenador deve:

- impedir dois executores de alterar a mesma fronteira sem estratégia de merge;
- compartilhar o mínimo de contexto comum;
- manter dependências explícitas;
- reconciliar resultados numa única visão;
- cancelar ou redirecionar trabalho invalidado por nova decisão;
- evitar que velocidade de fanout ultrapasse capacidade de review.

Paralelismo sem capacidade de integração aumenta fila e conflito; não é aceleração real.

## 14. Estratégia de roteamento

O roteamento usa evidência histórica, não reputação abstrata. Uma matriz local pode comparar por classe:

- taxa de aprovação na primeira tentativa;
- frequência e gravidade de correções;
- duração mediana e cauda;
- indisponibilidade;
- tamanho médio das mudanças;
- custo quando confiável;
- ocorrência de falso sucesso;
- necessidade de contexto adicional.

Regras recomendadas:

- começar com roteamento simples e explícito;
- trocar executor após reincidência ou incompatibilidade clara;
- não usar fallback silencioso em tarefa com efeitos mutáveis;
- registrar modelo e configuração efetivos;
- reavaliar somente com amostra suficiente;
- preservar caminho manual quando automação estiver indisponível.

## 15. Telemetria operacional

Telemetria mede o processo, não o conteúdo do trabalho.

### Metadados úteis

- identificadores aleatórios de evento, tarefa e tentativa;
- instante e duração;
- workflow e classe;
- capacidade/modelo efetivo;
- resultado técnico e resultado do review;
- motivo padronizado de correção ou bloqueio;
- contagens de checks;
- volume numérico de mudança;
- tokens e custo somente quando confiáveis;
- presença de especialista e quantidade de achados materiais.

### Conteúdo proibido

- prompt e resposta completos;
- código, diff e nomes sensíveis;
- credenciais, tokens e segredos;
- dados pessoais;
- conteúdo real do produto;
- justificativas que revelem informação protegida.

### Uso correto

A telemetria serve para encontrar gargalos, ajustar decomposição e comparar capacidades. Não fecha portas, não substitui review e não converte amostra pequena em regra automática.

## 16. Segurança e privacidade

- menor privilégio por tarefa;
- somente leitura como padrão para descoberta, arquitetura e revisão;
- escrita restrita a fronteiras declaradas;
- proibição de segredos no contrato;
- dados sintéticos em testes;
- nenhuma ação externa sem autorização explícita;
- nenhuma limpeza automática de alterações preexistentes;
- detecção posterior de mudança não deve ser chamada de sandbox;
- processos persistentes exigem isolamento e ciclo de vida próprios;
- conteúdo externo é evidência não confiável, nunca instrução automática.

## 17. Taxonomia de falhas

| Classe | Exemplo conceitual | Tratamento |
|---|---|---|
| contrato inválido | campo obrigatório ausente | bloquear antes da execução |
| decisão ausente | arquitetura ou risco não aprovado | retornar à porta competente |
| indisponibilidade externa | serviço ou modelo inacessível | registrar, aplicar fallback deliberado ou aguardar |
| reprovação técnica | código ou documento incorreto | correção delimitada |
| violação de escopo | mutação fora da fronteira | bloquear e preservar evidência |
| evidência insuficiente | executor declara sucesso sem prova | não verificar; exigir check |
| resposta ambígua | efeito pode ter ocorrido sem confirmação | observar/reconciliar antes de repetir |
| conflito de baseline | estado anterior se mistura à entrega | separar autoria; nunca limpar automaticamente |
| repetição improdutiva | mesmo erro após correção | reduzir, trocar capacidade ou bloquear |
| risco material novo | mudança afeta segurança/arquitetura | interromper e pedir decisão |

## 18. Cenários de referência

### Análise documental

Uma unidade read-only recebe fontes, pergunta e formato de retorno. O executor produz achados. O coordenador confere as fontes e somente a síntese reconciliada é persistida.

### Mudança de código pequena

Arquitetura e plano já estão aprovados. A unidade declara arquivos permitidos, comportamento e testes. O executor altera e relata. O revisor procura regressão; o coordenador reexecuta os checks antes do aceite.

### Decisão arquitetural

Executores podem investigar alternativas em paralelo, sem editar a decisão final. O coordenador reconcilia critérios e divergências. O proprietário escolhe a alternativa material. Só então nasce um plano de implementação.

### Falha de provedor

O processo termina tecnicamente sem entrega. A telemetria registra indisponibilidade, não reprovação de qualidade. O coordenador decide aguardar, trocar capacidade ou reduzir a tarefa, respeitando o limite de tentativas.

### Executor declara sucesso falso

O relato diz que o objetivo foi alcançado, mas a evidência falha. A unidade vai para correção ou bloqueio. O estado real prevalece sobre a narrativa.

### Efeito fora do escopo

Uma alteração aparece fora da fronteira autorizada. Nada é apagado automaticamente. O review bloqueia, preserva o baseline e solicita adjudicação.

## 19. Adoção progressiva

### Nível 1 — Manual disciplinado

Papéis, contrato, review e evidências existem em documentos ou tickets. Sem automação obrigatória.

### Nível 2 — Execução padronizada

Um adaptador valida contratos, inicia execuções e captura estados técnicos.

### Nível 3 — Evidência e telemetria

Checks e metadados sanitizados são agregados; o roteamento ainda é humano.

### Nível 4 — Roteamento assistido

O sistema recomenda capacidade com base no histórico, mas o coordenador confirma tarefas de risco.

### Nível 5 — Automação seletiva

Somente classes repetitivas, reversíveis e bem avaliadas ganham roteamento ou retry automático. Portas materiais continuam humanas.

Avançar de nível exige evidência de necessidade e capacidade de rollback. Maturidade não é medida pela quantidade de automação.

## 20. Critérios de conformidade

Uma implementação deste SOAP deve demonstrar:

- [ ] autoridade e papéis identificados;
- [ ] fonte de verdade consultada antes da execução;
- [ ] classificação proporcional ao risco;
- [ ] decisões e planos aprovados antes de mutação relevante;
- [ ] contrato mínimo por unidade;
- [ ] contexto e permissões reduzidos ao necessário;
- [ ] baseline preservado;
- [ ] execução e review separados;
- [ ] correções e retries limitados;
- [ ] falha externa diferenciada de reprovação;
- [ ] checks reobservados pelo coordenador;
- [ ] requisito ligado a evidência e status;
- [ ] telemetria sem conteúdo sensível;
- [ ] handoff recuperável;
- [ ] nenhuma publicação ou ação externa sem autorização.

## 21. Antipadrões

- enviar “faça tudo” a um executor;
- compartilhar o repositório inteiro quando bastam poucos artefatos;
- permitir que o modelo escolha e aprove o próprio escopo;
- aceitar texto convincente como evidência;
- repetir até funcionar sem budget;
- trocar modelo silenciosamente durante tarefa mutável;
- paralelizar tarefas com ownership sobreposto;
- registrar prompts e respostas para obter métricas;
- limpar o working tree para esconder conflito;
- criar orquestrador complexo antes de provar o fluxo manual;
- transformar toda tarefa simples em cerimônia arquitetural;
- tratar indisponibilidade do fornecedor como defeito da entrega;
- persistir saída bruta como decisão oficial.

## 22. Condições de redesign

Reavaliar o procedimento quando:

- a maior parte das tarefas exigir contexto persistente legítimo;
- o review se tornar gargalo maior que a execução;
- falso negativo de triagem ocorrer de forma recorrente;
- tarefas exigirem dados sensíveis que não possam ser minimizados;
- o volume exigir fila, leases e recuperação distribuída;
- múltiplos coordenadores precisarem atuar simultaneamente;
- automações externas precisarem de identidade e autorização próprias;
- telemetria demonstrar que um limite local piora qualidade ou custo.

Redesign deve preservar autoridade, evidência, segurança e reversibilidade, mesmo que estados ou ferramentas mudem.

## 23. Resultado final esperado

Uma equipe que adota o SOAP não depende de uma marca específica para operar. Ela possui um sistema no qual:

- demandas entram com intenção clara;
- decisões precedem implementação;
- tarefas são pequenas e contratadas;
- capacidades são escolhidas por adequação observada;
- executores trabalham sem autoridade implícita;
- revisão e adjudicação permanecem independentes;
- conclusão depende de evidência;
- falhas são classificadas honestamente;
- conhecimento sobrevive à troca de sessão, agente, modelo ou plataforma.

Esse é o conceito transferível. CLIs, APIs, agentes, modelos, arquivos e scripts são apenas adaptações locais desse sistema.
