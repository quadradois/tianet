# Descoberta — aviso de queda do WhatsApp no IMP-370

**Data:** 2026-09-08
**Status:** Descoberta concluída; decisão do proprietário aprovada em 2026-09-08
**Workflow / classificação:** discover / STANDARD
**Impacto agentic do produto:** NONE
**Delegação:** OpenCode somente leitura, resultado reconciliado pelo coordenador

## Problema e objetivo

O IMP-370 já sincroniza periodicamente o estado da conexão e devolve uma `QuedaDeConexao` quando observa a transição de pareada para não pareada. O worker chama essa varredura, mas descarta o retorno. O objetivo pendente é transformar essa transição em um aviso visível à operadora sem depender do próprio WhatsApp que caiu.

## Fatos revalidados

- `SincronizarConexoesWhatsApp.executar()` devolve uma lista de quedas e a transição é criada somente quando `estava_pareada` passa para estado não pareado, em `src/emprestimo/application/conexao_whatsapp.py`.
- `_VarreduraPeriodica.talvez_varrer()` preserva o retorno, porém `antes_do_ciclo()` o descarta em `src/emprestimo/worker/scheduler_worker.py`.
- A sincronização usa intervalo padrão de 300 segundos. Assim, a detecção pode atrasar até aproximadamente cinco minutos quando worker e provedor estão disponíveis.
- O contexto operacional lê o último estado persistido, e `frontend/src/components/shell/whatsapp-badge.tsx` já exibe o selo conectado/não conectado.
- Não existe service worker, assinatura Web Push, VAPID ou uso da Notification API no frontend atual.
- O adaptador Resend existe, mas e-mail está fora do MVP e não há conta contratada, conforme `docs/operations/contexto-externo.md`.
- Enviar o aviso pelo mesmo canal WhatsApp não atende ao requisito quando a conexão está indisponível.
- A auditoria já registra pareamento/desparelhamento como histórico append-only; ela não representa estado ativo consumível pela UI.

## Alternativas

| Alternativa | Avaliação |
|---|---|
| Alerta persistente dentro do TiaNet | Reaproveita detecção, persistência e shell atuais. Funciona quando a operadora voltar ou permanecer no sistema, sem contratação externa. É a menor solução coerente. |
| Push do navegador | Exige service worker, assinatura, chaves, permissão e operação ausentes. A Notification API sem Web Push não resolve aba fechada. Deixar como evolução, se houver necessidade comprovada. |
| E-mail, SMS ou segundo canal | Permite avisar fora do sistema, mas exige serviço, credencial, custódia e decisão comercial inexistentes. Reavaliar apenas após contratação explícita. |

## Recomendação arquitetural

Adicionar à conexão existente `queda_detectada_em`, um estado nullable que representa o alerta ativo. Quando uma leitura real do provedor observar a borda pareada → não pareada, a própria sincronização persiste esse instante antes do commit e ainda sob o advisory lock do tenant. O worker continua sendo o detector periódico; a consulta da tela de conexão pode detectar a mesma transição antes dele porque reutiliza a sincronização. A desconexão solicitada pela operadora não cria alerta de queda. No novo pareamento confirmado, a sincronização limpa o alerta. A auditoria preserva o histórico; portanto não é necessária uma tabela histórica paralela para o primeiro slice.

O contexto operacional expõe `alerta_queda_ativa` e `queda_detectada_em`. A shell mostra um banner destacado além do selo enquanto a queda estiver ativa, com link para a tela de conexão. O aviso não terá dispensa manual inicial: permitir ocultá-lo enquanto a conexão continua caída enfraqueceria o objetivo. A recuperação confirmada limpa o aviso automaticamente.

Essa recomendação não promete notificação com navegador fechado. Se esse comportamento for necessário, um canal externo independente ou Web Push vira decisão e plano próprios.

## Menor slice após aprovação

1. Migration aditiva e entidade/repositório para `queda_detectada_em`.
2. Persistência idempotente da transição dentro da sincronização, ainda sob o lock, e limpeza na recuperação; desconexão manual não cria alerta.
3. Exposição no contexto operacional e banner acessível na shell.
4. Testes que demonstrem: uma queda cria um alerta; permanência desconectada não duplica; recuperação limpa; desconexão manual não cria alerta; falha do provedor não inventa queda; UI exibe e remove conforme o estado.

## Critério de redesign

Redesenhar se o proprietário exigir aviso com o TiaNet fechado, retenção operacional independente da auditoria, ciência manual com responsável, ou canal externo. Essas escolhas criam novas responsabilidades e não devem ser inferidas desta descoberta.

## Revisão da delegação

O OpenCode encontrou corretamente a transição descartada e comparou as alternativas. O coordenador confirmou os fatos nas fontes. A execução não alterou arquivos e o Harness não detectou violação de mutação.

A entrega bruta recebeu `CORREÇÃO / SCOPE_VIOLATION`: o agente leu arquivos relacionados fora de `allowedPaths` e tentou um comando não autorizado. Nenhum segredo foi lido, mas o contrato de tarefa não foi integralmente respeitado. As duas primeiras tentativas no Nemotron foram interrompidas por sobrecarga 502; a terceira usou Muse Spark 1.3. Não existe quarta tentativa automática para a mesma tarefa.

## Porta de decisão

Decisão aprovada pelo proprietário em 2026-09-08: alerta persistente dentro do TiaNet, sem segundo canal nesta etapa, sem dispensa manual e removido automaticamente após reconexão confirmada. A aprovação do desenho não fecha a porta G5 do plano de execução.
