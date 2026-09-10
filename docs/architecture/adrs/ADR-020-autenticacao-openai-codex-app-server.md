# ADR-020: Autenticação OpenAI pelo Codex App Server isolado

> **Status:** Aceito  
> **Data:** 2026-09-09  
> **Autor(es):** Engenharia  
> **Revisor(es):** AI Architect Senior; coordenação Codex  
> **Aprovação:** Proprietário / 2026-09-09  
> **Substitui:** —  
> **Substituído por:** —

---

## Contexto

O proprietário quer testar na prática o uso da própria conta ChatGPT/Codex antes
de escolher o provedor de inferência do copilot. O repositório comunitário
`openai-oauth` usa endpoint interno e não atende às fronteiras de segurança e
operação do TiaNet. A OpenAI oferece o Codex App Server oficial, com login
ChatGPT por device code e protocolo local por `stdio`.

Executar o App Server dentro da API financeira ou do frontend ampliaria o alcance
da credencial. Persistir o device code na idempotência genérica também
transformaria um segredo efêmero em dado durável.

## Decisão

O piloto usa um serviço `agent` privado e isolado como único dono do Codex App
Server e de seu volume de credenciais. A comunicação com o filho usa `stdio`.
A API TiaNet aplica autenticação e RBAC e chama o serviço por contrato interno;
frontend, API e banco nunca recebem tokens OpenAI.

A comunicação API→`agent` usa HTTP sobre socket Unix em volume runtime mínimo,
compartilhado somente entre esses dois serviços. O `agent` conserva sua rede de
egress exclusiva e não participa da rede da API/PostgreSQL. O diretório é
`0750`, o socket é `0660`, a API só pode conectá-lo e o segredo interno continua
obrigatório. Não existe listener TCP ou fallback TCP.

A rede do `agent` é interna. Seu único caminho de saída é um proxy CONNECT
dedicado, sem volumes ou credenciais, que aceita somente porta 443 e hosts
OpenAI explicitamente permitidos. O proxy recusa resolução para endereços
privados e limita concorrência, cabeçalho, deadlines e bytes transferidos. Assim, a rota
para portas publicadas no host também permanece fechada.

O primeiro incremento permite somente inicialização, `account/login/start` com
`chatgptDeviceCode`, `account/login/cancel`, `account/read`, `model/list`,
`account/rateLimits/read` e `account/logout`. Nenhuma conversa, tool, shell ou
leitura de arquivo é permitida.

`GET /platform/openai/conexao` lê apenas snapshot local. O diagnóstico de plano,
modelos e limites usa `GET /platform/openai/diagnostico`, explícito e limitado.
O logout exige `Idempotency-Key`.

Fica isento de `Idempotency-Key` somente
`POST /platform/openai/conexao/login`. O resultado é um device code temporário;
o replay genérico o persistiria e poderia devolvê-lo depois da validade. Enquanto
o desafio estiver ativo, o serviço devolve o mesmo valor da memória; depois de
10 minutos, cancela a tentativa antes de criar outra. A exceção é fechada.

Mutações são serializadas por Tenant. Geração e `loginId` impedem que conclusão
ou diagnóstico antigos restaurem estado após logout. Logout com login pendente
cancela a tentativa, reinicia o filho, executa logout e confirma conta ausente
antes de anunciar desconexão.

## Alternativas consideradas

| Opção | Motivo da rejeição |
|---|---|
| Filho da API TiaNet | Mistura credencial de IA ao processo com acesso financeiro e exige migração posterior |
| Filho do frontend | Estado e segredo ficam acoplados ao BFF e aos seus workers/restarts |
| Proxy `openai-oauth` | Projeto comunitário, endpoint interno e fronteiras insuficientes |
| API OpenAI por chave | Alternativa válida futura, mas não testa a conta ChatGPT/Codex solicitada |

## Consequências

- O piloto exige imagem e volume próprios para o `agent`.
- Um volume runtime separado contém somente o socket Unix; ele não contém
  credencial, código ou configuração da API.
- O App Server experimental fica fixado por versão e schema.
- Nenhum dado TiaNet ou de cliente é enviado nesta etapa.
- OpenRouter, NVIDIA e OmniRoute ficam em espera e não atuam como fallback.
- Logout comprova remoção local; revogação remota não é prometida.
- A preparação local antecede o IMP-356 sem contar como sua execução e sem
  remover IMP-359 ou fechar GATE-E1b/E3.

## Validação

O adapter recusa métodos fora da allowlist, frames acima de 1 MiB, respostas
inválidas, timeout acima de 15 segundos e resultado incerto sem reconciliação.
Testes contam zero chamadas downstream no polling, cobrem login/logout
concorrentes e demonstram o isolamento do container antes do login real.
Também verificam proprietário/permissões do socket, recuperação segura de
socket residual, backlog/timeout, health pelo mesmo canal e ausência de alcance
do `agent` à API e ao PostgreSQL.

## Referências

- [Arquitetura detalhada](../reviews/openai-codex-auth-pilot-2026-09-09.md)
- [Plano de execução](../../governance/agents/openai-codex-auth-plano-execucao-2026-09-09.md)
- [Discovery](../../audits/discoveries/openai-oauth-chatgpt-codex-2026-09-09.md)
- [Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [ADR-003](ADR-003-escopo-single-tenant-do-v1.md)
- [ADR-019](ADR-019-isencao-de-idempotency-key-nas-escritas-da-conexao-de-whatsapp.md)

---

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-09 | Registra App Server isolado, recorte administrativo e exceção fechada do device code. |
| 1.1.0 | 2026-09-09 | Define HTTP sobre socket Unix como canal unidirecional API→agent, sem bridge ou fallback TCP. |
| 1.2.0 | 2026-09-09 | Fecha o egress em proxy CONNECT com allowlist após a prova local detectar alcance indireto ao host. |
