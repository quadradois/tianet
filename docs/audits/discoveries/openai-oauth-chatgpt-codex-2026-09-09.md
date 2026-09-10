# Discovery — openai-oauth e uso de conta ChatGPT/Codex no TiaNet

**Identificador local:** `openai-oauth-chatgpt-codex-2026-09-09`

**Versão:** 1.1.0

**Data da consulta:** 2026-09-09

**Status:** o repositório comunitário permanece somente como referência; a integração oficial pelo Codex App Server com login ChatGPT é candidata viável a uma nova etapa de arquitetura e prova sintética.

**Workflow / classificação / impacto:** `discover` / `ARCHITECTURAL` / `PRESENT`.

## Pergunta e conclusão

O proprietário solicitou avaliar o repositório [EvanZhouDev/openai-oauth](https://github.com/EvanZhouDev/openai-oauth) como forma de agregar valor ao produto e aproximar o TiaNet dos modelos da OpenAI.

O projeto possui mérito técnico: expõe `/v1/responses`, `/v1/chat/completions` e `/v1/models`, traduz chamadas de tools e permite selecionar modelos Codex disponíveis na conta. Isso o torna uma referência útil para estudar compatibilidade OpenAI; executar um laboratório local continua condicionado a esclarecer se o uso pretendido é autorizado.

Ele não deve ser incorporado ao TiaNet. O projeto transforma credenciais OAuth de uma conta ChatGPT/Codex em um proxy genérico e chama o endpoint interno `https://chatgpt.com/backend-api/codex`. É um projeto comunitário não oficial, sem autenticação na API local de inferência e dependente do catálogo e dos limites da conta.

Após o proprietário esclarecer que deseja apenas oferecer um botão de login e consumir a franquia da própria conta paga, foi localizada uma alternativa oficial distinta: o [Codex App Server](https://learn.chatgpt.com/docs/app-server). A OpenAI documenta essa interface para incorporar Codex em produtos próprios. Ela expõe login ChatGPT gerenciado pelo navegador ou por device code, renovação automática de tokens, catálogo de modelos e leitura dos limites da conta. Portanto, a intenção é tecnicamente plausível sem reutilizar o código ou o endpoint privado do `openai-oauth`.

A recomendação é:

1. não integrar nem copiar `openai-oauth`;
2. abrir uma etapa Architect própria para o Codex App Server oficial, sem substituir por esta descoberta a direção OpenRouter/NVIDIA já aprovada;
3. prototipar somente com dados sintéticos e transporte local `stdio`, usando o fluxo oficial `chatgptDeviceCode` quando o app-server estiver na VPS;
4. provar isolamento, política de dados, consumo da conta, tools e ausência de capacidades de shell/arquivo antes de considerar piloto;
5. manter a API oficial por chave de projeto como alternativa contratual e operacional.

## Evidência e método

Foram consultados:

- [repositório e documentação do projeto](https://github.com/EvanZhouDev/openai-oauth);
- [licença Apache-2.0](https://github.com/EvanZhouDev/openai-oauth/blob/main/LICENSE);
- [política de privacidade do projeto](https://github.com/EvanZhouDev/openai-oauth/blob/main/PRIVACY.md);
- [termos de uso da OpenAI](https://openai.com/policies/terms-of-use/);
- [uso oficial do Codex com planos ChatGPT](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan);
- [separação entre cobrança ChatGPT e API](https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform);
- [controles de dados da API](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint);
- [privacidade de dados empresariais](https://openai.com/business-data/);
- [autenticação do app-server oficial do Codex](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md);
- [documentação oficial do Codex App Server](https://learn.chatgpt.com/docs/app-server);
- [autenticação oficial do Codex](https://learn.chatgpt.com/docs/auth).

O código `main`, commit `ec7dab2fcd8dab9da970a7a2b5dc34046c94905e`, e a tag `v2.0.0` foram inspecionados em clone temporário somente leitura. Não houve instalação, login, leitura de `~/.codex/auth.json`, chamada de modelo ou acesso a qualquer token.

## Funcionamento observado

O pacote `openai-oauth` versão 2.0.0 inicia por padrão um servidor em `127.0.0.1:10531`. O servidor:

- lê credenciais de `$CODEX_HOME/auth.json` ou `~/.codex/auth.json`;
- renova access tokens por `https://auth.openai.com/oauth/token`;
- envia Bearer token e `chatgpt-account-id` ao backend Codex;
- consulta o catálogo de modelos disponível para aquela conta;
- converte Chat Completions para o protocolo usado pelo endpoint Responses do Codex;
- oferece texto, streaming, tools, reasoning e imagens nas superfícies documentadas.

O arquivo local grava access token, refresh token, ID token e account ID em JSON com permissão solicitada `0600`, mas sem criptografia própria. No Windows, a semântica POSIX de `0600` não constitui por si só proteção equivalente a cofre de credenciais. O arquivo padrão é o mesmo usado pelo Codex, então comprometê-lo compromete a sessão pessoal e interfere no ambiente de engenharia.

A rota de inferência do proxy não valida API key ou outro segredo do chamador. O controle tokenizado encontrado no CLI protege comandos internos de status/stop, não os endpoints `/v1`. O loopback reduz a exposição local; publicar em interface não loopback faz qualquer processo ou host com alcance à porta consumir a conta autenticada.

## Valor potencial

| Uso | Valor | Limite |
|---|---|---|
| Teste local de compatibilidade | Alto: endpoint OpenAI-compatible e tools facilitam experimentar clientes | Usa conta/limite Codex e contrato não demonstrado para backend genérico |
| Referência de tradução | Médio: código mostra adaptação de Chat Completions, Responses e tools | Não é necessário copiar a biblioteca para o cliente `httpx` do TiaNet |
| Benchmark sintético de modelos OpenAI | Potencial | Somente após esclarecer se esse uso fora de cliente Codex oficial é permitido |
| Runtime do TiaNet | Baixo | Credencial pessoal, endpoint interno, ausência de auth/SLA e política de dados não demonstrada como aceitável |
| Login de cada usuário com ChatGPT | Incompatível com o v1 | Muda BYOK de uma credencial do serviço para credenciais pessoais por operador e exige extensão de navegador |
| Encadear com OmniRoute | Valor líquido negativo | Dois gateways, duas traduções e mais pontos de falha sem resolver contrato ou privacidade |
| Codex App Server oficial | Alto potencial para a intenção esclarecida | Exige novo adapter, isolamento forte e prova de tools; a superfície foi desenhada para Codex, não como substituição transparente de Chat Completions |

## Fluxo oficial aplicável à intenção

O fluxo recomendado para prova é:

1. a Operadora autenticada no TiaNet seleciona **Conectar conta OpenAI**;
2. o backend inicia um processo oficial `codex app-server` isolado e comunica por `stdio`/JSON-RPC;
3. o backend chama `account/login/start` com `type: "chatgptDeviceCode"`;
4. o frontend apresenta a URL oficial `https://auth.openai.com/codex/device` e o código devolvido pelo servidor;
5. após `account/login/completed`, o TiaNet confirma `authMode`, `planType`, modelos disponíveis e limites pelo próprio protocolo;
6. a desvinculação local usa `account/logout`; tokens nunca passam pelo navegador do TiaNet nem entram no banco de domínio. A documentação consultada não demonstra revogação remota por esse método, que permanece desconhecida e precisa de mecanismo oficial separado ou expiração comprovada.

O browser flow também existe, mas o callback é hospedado localmente pelo app-server. Como o TiaNet será executado em VPS e acessado por navegador remoto, device code evita depender de um callback `localhost` na máquina errada. O WebSocket do app-server é experimental e explicitamente não suportado para produção; a integração deve manter o processo como filho local via `stdio` ou reabrir a decisão se a topologia exigir transporte remoto.

O app-server também possui capacidades de comando, arquivos e ferramentas. Negar pedidos de aprovação não garante que uma operação já permitida deixe de executar. A prova deve tornar shell e filesystem indisponíveis ou bloqueá-los efetivamente por isolamento externo, com diretório, configuração, credenciais e armazenamento próprios que não herdem a sessão Codex de engenharia. Tentativas adversariais precisam demonstrar o bloqueio. As seis capacidades TiaNet entram somente por adapter fechado. A alternativa mais direta, `dynamicTools`, está documentada como experimental; isso é um bloqueador de piloto até a arquitetura provar uma superfície estável, por exemplo MCP restrito, ou a OpenAI promover esse contrato.

Ler `account/rateLimits/read` mostra a franquia observada, mas não define o orçamento interno de um turno Codex. A prova deve contar inferências, retries, etapas e chamadas de ferramenta, fixar um modelo nominal e interromper sem retomada automática após resultado incerto. A certificação do cliente Chat Completions existente não se transfere ao App Server.

## Elegibilidade contratual e comercial

O README declara que o projeto é comunitário, não afiliado nem endossado pela OpenAI, e que usa os mesmos tokens OAuth do Codex para obter acesso sem comprar créditos de API. Isso não é equivalente a uma API oficial gratuita.

A OpenAI documenta que Codex é incluído em planos ChatGPT elegíveis e pode autenticar oficialmente com ChatGPT. O Codex App Server também é documentado como interface para integração profunda em produto próprio, incluindo autenticação, conversas, aprovações e eventos. Isso torna o componente oficial diferente do proxy comunitário. A documentação não afirma que o OAuth ChatGPT seja uma credencial genérica da OpenAI API: ele autentica a superfície Codex e segue permissões, política e limites do workspace ChatGPT.

Os termos pessoais também proíbem compartilhar credenciais ou disponibilizar a conta a terceiros e proíbem extração programática de dados/output fora das permissões do serviço. Não se conclui neste discovery que todo uso do repositório viola os termos; conclui-se que **não existe evidência suficiente para qualificá-lo como rota produtiva autorizada**. Usá-lo exigiria confirmação escrita da OpenAI para este caso de uso e tipo de conta.

ChatGPT e API possuem cobrança separada. “Sem API key” significa consumir a franquia/créditos Codex da conta, não obter API gratuita. Limites, modelos e disponibilidade variam com o plano e podem mudar sem o contrato de estabilidade esperado pelo produto.

Para a OpenAI, a integração produtiva clara e sustentável é a API oficial ou acordo empresarial aplicável. Isso remunera o uso pelo canal previsto, fornece termos para aplicações e permite controles de organização/projeto.

## Privacidade e DR-005

O TiaNet pode enviar PII integral de terceiros segundo a DR-005, desde que o provedor tenha política aceitável, sem treino, retenção declarada e subprocessadores conhecidos.

Na API oficial, a OpenAI declara que entradas e saídas não são usadas para treino por padrão; há retenção padrão de abuse monitoring e, para organizações elegíveis, Modified Abuse Monitoring ou Zero Data Retention. Em contas pessoais ChatGPT/Codex, conteúdo pode ser usado para treino quando o usuário não desabilita essa opção, e os controles são da conta pessoal.

O `openai-oauth` não oferece projeto de API, ZDR, DPA, separação por Tenant ou prova de que as políticas da API se aplicam ao endpoint interno Codex. Mesmo uma conta ChatGPT Business não transforma automaticamente esse proxy comunitário em integração API autorizada. Portanto:

- nenhum dado real, CPF, telefone, valor ou conversa deve passar pelo proxy;
- opt-out pessoal de treinamento não basta para cumprir o aceite da DR-005;
- a rota reprova o filtro de elegibilidade antes mesmo do benchmark de qualidade.

## Compatibilidade técnica com as invariantes

| Invariante TiaNet | Resultado |
|---|---|
| API OpenAI-compatible | Atende a forma básica |
| Tools | Implementadas e cobertas por testes do projeto; comportamento real exigiria prova |
| Modelo nominal fixo | Possível por allowlist/configuração, mas catálogo continua dependente da conta Codex |
| Sem fallback automático | Não foi observado roteamento multiprovedor; indisponibilidade do backend permanece fora do controle |
| Chave própria do cliente | Não atende: usa sessão pessoal ChatGPT/Codex e refresh token |
| Segredo fora de arquivo genérico | Não atende ao desenho atual: token fica no `auth.json` local |
| Autenticação entre TiaNet e gateway | Não atende: endpoints `/v1` não autenticam o chamador |
| Política de dados e ZDR | Não atende sem acordo/controle explícito aplicável ao endpoint |
| Operação e SLA | Não atende: endpoint interno e projeto comunitário sem garantia |
| Isolamento por Tenant | Não atende sem construir camada adicional, que ainda deixaria a conta compartilhada |

## Comparação com as rotas já analisadas

| Rota | Papel atual | Produção/piloto real |
|---|---|---|
| OpenRouter + Ling Fin gratuito | Candidato principal sob ZDR e tools | Elegível após certificação e reconfirmação |
| NVIDIA direta + Nemotron 3 Super | Comparador sintético forte | Trial atual proíbe produção |
| OmniRoute restrito | Gateway opcional para os provedores anteriores | Bloqueado até eliminar tool-call textual e passar prova |
| `openai-oauth` + conta ChatGPT/Codex | Referência/laboratório local | Inelegível sem autorização explícita da OpenAI e redesign de credenciais/operação |
| Codex App Server + login ChatGPT | Candidato oficial para nova arquitetura | Elegível para prova sintética; piloto depende de estabilidade das tools, isolamento e política de dados |
| API oficial OpenAI | Alternativa futura paga e contratualmente clara | Pode ser qualificada em novo slice/modelo/orçamento |

## Condições mínimas por alternativa

O proxy comunitário `openai-oauth` só poderia ser reconsiderado se houvesse:

1. confirmação oficial escrita de que a conta e o endpoint Codex podem sustentar este tipo de aplicação;
2. conta organizacional dedicada, nunca credencial pessoal compartilhada;
3. contrato de dados compatível com PII de terceiros, retenção e ausência de treino;
4. autenticação forte na API local, rede privada e cofre para refresh token;
5. modelo nominal, limites, métricas, revogação e isolamento compatíveis com o processo/Tenant único vigente; expansão multitenant exige decisão própria;
6. prova de tools nativas, uma tentativa upstream por tentativa admitida, resolução e falha fechada;
7. comparação econômica com a API oficial, incluindo créditos Codex consumidos e risco operacional.

Cumprir os itens técnicos sem a autorização contratual não torna a rota elegível.

O Codex App Server oficial pode seguir para Architect e prova sintética sem exigir a mesma autorização excepcional do proxy, desde que:

1. a política do workspace ChatGPT seja compatível com os dados admitidos pela DR-005; caso contrário, a prova permanece estritamente sintética;
2. tokens, configuração, sessão e armazenamento do processo sejam isolados do ambiente de engenharia e de outros Tenants;
3. logout local, expiração e eventual revogação remota sejam distinguidos e testados; trabalhos antigos não podem continuar após a desvinculação;
4. shell, filesystem, rede lateral e ferramentas não autorizadas estejam mecanicamente indisponíveis, com testes adversariais;
5. as seis tools e três permissões usem uma superfície estável e fechada; `dynamicTools` experimental não atende piloto;
6. modelo, inferências, retries, etapas, tools, tempo e consumo tenham limites próprios, métricas e falha fechada;
7. a comparação com OpenRouter e API oficial use fixtures equivalentes e não herde certificação de outro adapter.

## Decisão recomendada

Não incorporar o repositório ao produto nem ao OmniRoute. Reabrir Architect para comparar duas rotas oficiais: Codex App Server com login ChatGPT e API OpenAI com chave de projeto. A primeira corresponde à intenção de consumir a franquia da conta paga; a segunda conserva a integração API tradicional. OpenRouter/NVIDIA continuam como direção aprovada até nova decisão formal.

## Revisão especializada

O `ai_architect` revisou este discovery em missão `READ_ONLY`, sem credenciais, dados reais ou acesso à sessão ChatGPT/Codex. Na primeira leitura confirmou os bloqueadores operacionais e solicitou quatro precisões documentais: laboratório condicionado a esclarecimento oficial, referência à aprovação efetiva do plano, política de dados tratada como não demonstrada e preservação do escopo single-tenant vigente. Após as correções, retornou `APPROVED` para prontidão documental, sem pendência material. O parecer não autoriza laboratório, integração nem fecha gates.

Após a descoberta do App Server oficial, nova revisão pediu isolamento mecânico, separação entre logout e revogação, condições próprias por alternativa e orçamento observável por turno. As quatro correções foram incorporadas e a segunda leitura retornou `APPROVED` para prontidão documental. Tools estáveis, isolamento e controle de execução continuam dependentes de prova; o parecer não altera o plano aprovado.

## Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.1.0 | 2026-09-09 | Reavalia a intenção esclarecida e identifica o Codex App Server oficial como rota viável para prova sintética com login ChatGPT, separada do proxy comunitário. |
| 1.0.0 | 2026-09-09 | Analisa arquitetura, OAuth, tools, credenciais, termos, privacidade e valor do openai-oauth para o TiaNet. |
