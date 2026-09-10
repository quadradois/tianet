# Checklist de entrega — TiaNet, VPS e Mercado Pago

**Data:** 2026-09-08
**Status:** Checklist de acompanhamento; execução pendente por etapa.
**Autorização:** proprietário solicitou criar o checklist e incluir Mercado Pago após a implantação na VPS.
**Classificação desta edição:** SMALL, documental.
**Impacto agentic desta edição:** NONE — organiza pendências existentes, sem alterar prompts, capacidades, budgets ou autorização de agentes. Futuras tarefas de Copilot/IA exigem triagem própria.

## Objetivo e sequência

Concluir a conexão do WhatsApp, certificar a versão, publicar o TiaNet na VPS e integrar recebimentos pelo Mercado Pago. O fluxo financeiro previsto é Devedor → Credor, para pagamento do acerto; não é assinatura do SaaS.

Sequência: **concluir PLAN-034 → certificar release → implantar e verificar IMP-359 → integrar e homologar Mercado Pago → liberar pagamentos**.

Este checklist aponta trabalho e decisões pendentes; não substitui os planos, ADRs ou GATE-E, não declara arquitetura de pagamentos aprovada e não autoriza publicação por si só. Marcar uma tarefa exige registrar evidência, data e responsável. Itens já implementados continuam abertos até a verificação necessária para a entrega.

## 1. Concluir a conexão do WhatsApp

- [x] Conferir branch, HEAD e alterações preexistentes; reconciliar o [plano](../../implementation/plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md) e o [backlog do PLAN-034](../../implementation/backlogs/PLAN-034-execution-backlog.md) com o código atual. Ambos atualizados para 1.2.0 em 2026-09-08.
- [x] Aprovar ou ajustar a recomendação da [descoberta do aviso de queda](DESCOBERTA-IMP-370-AVISO-QUEDA.md): alerta persistente dentro do TiaNet, sem segundo canal nesta etapa e remoção automática após reconexão. Aprovado pelo proprietário em 2026-09-08.
- [x] Concluir o IMP-370: leitura do token, atualização de estado e aviso ativo; verificar queda, recuperação e ausência de avisos duplicados. Evidência em [VERIFICACAO-IMP-370-AVISO-QUEDA.md](VERIFICACAO-IMP-370-AVISO-QUEDA.md).
- [x] Rever o intervalo de sincronização implementado e alinhar a documentação ao comportamento confirmado. Intervalo padrão confirmado em 300 segundos; limite registrado no plano e na verificação.
- [x] Executar testes do worker, conexão, token, API e jornadas da tela; registrar resultados no fechamento do PLAN-034. Matriz concluída em 2026-09-08.

**Saída:** critérios do IMP-370 demonstrados e empacotados em commits locais, sem pendência funcional identificada na matriz. Integração do PLAN-034 e publicação permanecem nas etapas seguintes.

## 2. Preparar a versão de entrega

- [x] Revisar e incluir o Harness na versão a entregar, preservando as normas da SPEC-004 e do ALP-001. Commit local `7d3a5e3`.
- [x] Executar os gates backend, frontend, contratos, migrations e jornadas definidos pelos planos sobre o commit candidato. Gates repetidos sobre `b99cb81` antes desta reconciliação exclusivamente documental; todos aprovados.
- [x] Verificar login/permissões, cadastro, empréstimo, cálculo do acerto, lançamento de pagamento e comunicação nas jornadas aplicáveis. A matriz principal de 156 cenários Playwright passou em 2026-09-08, incluindo 8 jornadas compostas contra a stack real descartável; dez reexecuções focais elevaram o total observado a 166 invocações aprovadas.
- [x] Classificar falhas e avisos; resolver bloqueios e registrar ressalvas aceitas por quem tem autoridade. As interrupções observadas foram encerramento transitório do servidor Next durante sequências longas e Docker Desktop desligado após a queda da sessão; as suítes afetadas passaram isoladamente, e a estabilização visual foi demonstrada em execuções consecutivas.
- [x] Atualizar backlog, handoff e evidências e obter autorização para os commits locais. Autorização concedida pelo proprietário em 2026-09-08; push, PR, merge e publicação continuam sem autorização.
- [ ] Identificar o commit/imagem de release e o procedimento de rollback, sem restaurar ou apagar trabalho alheio automaticamente.

**Saída:** versão identificada e verificada. Os testes do Harness não substituem a certificação do produto.

**Baseline atualizado da preparação em 2026-09-08:** branch `feat/imp-370-worker-le-o-token`, baseline anterior `b737c20`. A série local contém `7d3a5e3` (Harness), `f1b3c8d` (backend e migration), `9473e0d` (frontend e testes) e o commit documental que contém este checklist. O `gate:full` não deve ser chamado diretamente quando houver evidências visuais não consolidadas porque termina com `git checkout` de PNGs; executar suas etapas individualmente e acrescentar `quality:migrations`, `harness:check` e `harness:test`.

**Certificação local em 2026-09-08:** backend completo, ciclo Alembic, lint/typecheck/build, 72 testes unitários frontend, 82 de componentes, 42 de contrato, 137 de BFF e a matriz principal de 156 cenários Playwright passaram. Também passaram dez reexecuções focais de acessibilidade e captura visual. A [recertificação visual aditiva](../../audits/reports/tianet-release-candidate-visual-recertification-2026-09-08.md) confere 56/56 SHA-256, com 28 evidências desktop, 28 mobile, 44 regeneradas e 12 preservadas. A [verificação da candidata](VERIFICACAO-RELEASE-CANDIDATA-TIANET.md) registra o método, as falhas transitórias e os limites.

## 3. Preparar a VPS — IMP-359

- [ ] Inspecionar a VPS e confirmar acesso, sistema, recursos, serviços existentes e domínio/DNS. A documentação registra VPS provisionada; estado atual precisa de observação.
- [ ] Configurar acesso administrativo, atualizações e firewall; manter banco e API interna sem exposição pública indevida.
- [ ] Preparar configuração de produção, reverse proxy e HTTPS para o frontend, com renovação de certificado.
- [ ] Configurar segredos fora do Git/imagens/logs e definir sua custódia e recuperação.
- [ ] Repassar `WHATSAPP_TOKEN_ENCRYPTION_KEY` aos serviços que a utilizam; conferir credenciais Evolution e precedência do token no ambiente.
- [ ] Configurar banco persistente, migrations ordenadas, healthchecks e reinício dos processos.
- [ ] Automatizar backup do PostgreSQL e demonstrar restauração em ambiente controlado, sem sobrescrever produção.
- [ ] Preparar entrega/CD e demonstrar rollback compatível com as migrations e os dados.
- [ ] Configurar logs, monitoramento, alertas e procedimentos de recuperação.
- [ ] Reconciliar o checklist completo do [IMP-359](../../implementation/backlogs/PLAN-033-execution-backlog.md): separar requisitos já satisfeitos de itens ainda aplicáveis ao Copilot. Não declarar esse item encerrado só porque o frontend abriu.

**Saída:** infraestrutura pronta para implantação supervisionada, recuperação demonstrável e critérios do IMP-359 rastreáveis.

## 4. Publicar e validar o TiaNet

- [ ] Confirmar autorização de publicação e janela da mudança; registrar baseline e cópia de segurança quando houver dados.
- [ ] Implantar a versão identificada, aplicar migrations e configurar o primeiro acesso administrativo de forma segura.
- [ ] Validar HTTPS, login, permissões, API interna, banco e worker no ambiente publicado.
- [ ] Validar conexão e envio WhatsApp em cenário controlado autorizado; conferir o aviso de queda e recuperação.
- [ ] Reconciliar a medição de logout repetido com as evidências já obtidas e só então tratar a instância de teste antiga, conforme IMP-359; exclusão exige autorização aplicável.
- [ ] Registrar testes operacionais, recuperação, pendências e aceite da publicação.

**Saída:** endereço HTTPS estável e TiaNet operacional na VPS. Só então configurar e homologar o webhook produtivo de pagamentos.

## 5. Mercado Pago — decisões e desenho

- [ ] Confirmar modalidades: PIX, checkout/link ou combinação; escolher a integração oficial compatível. Não presumir que toda modalidade tem o mesmo contrato de webhook.
- [ ] Confirmar conta recebedora do Credor, aplicação no provedor e disponibilidade de credenciais de teste/produção, sem registrar valores secretos.
- [ ] Definir cobrança do acerto calculado pelo Motor: valor, validade, referência ao empréstimo/acerto e regras para pagamento parcial ou excedente.
- [ ] Definir comportamento para expiração, cancelamento, estorno/contestação e conciliação manual; não inventar plano de parcelas.
- [ ] Formalizar a exceção de ingresso público para Mercado Pago, pois a governança atual restringe webhooks públicos. Definir a fronteira de recepção sem expor toda a API.
- [ ] Desenhar vínculo entre cobrança, pagamento do provedor e lançamento financeiro, preservando isolamento, idempotência e auditoria append-only.
- [ ] Preparar e aprovar o plano específico de implementação, com cenários de teste e critérios de liberação. Não presumir G5 encerrado pela inclusão neste checklist.

**Saída:** decisões e contrato de integração definidos. Levantamento de requisitos pode começar antes da VPS; configuração/homologação produtiva fica depois dela, conforme a sequência solicitada.

## 6. Mercado Pago — implementar, homologar e liberar

- [ ] Implementar geração de cobrança e apresentação do pagamento conforme a modalidade aprovada.
- [ ] Implementar endpoint HTTPS de notificações e validar autenticidade segundo o contrato oficial da modalidade escolhida.
- [ ] Consultar o recurso na API do Mercado Pago e conferir conta recebedora, referência, valor, moeda e estado antes de reconciliar o pagamento; retorno do navegador não prova quitação.
- [ ] Tratar notificações repetidas e fora de ordem sem duplicar lançamento; prever retomada após falha e resposta conforme o protocolo do provedor.
- [ ] Configurar URL, eventos e segredo de webhook no ambiente correto, com acesso ao painel autorizado.
- [ ] Testar pagamento aprovado, pendente/rejeitado, expiração/cancelamento e estorno quando aplicáveis; cobrir divergências de valor/referência e assinatura inválida.
- [ ] Demonstrar que webhook duplicado ou falha durante o processamento não altera o saldo duas vezes; conciliar auditoria, pagamento e Motor.
- [ ] Validar exibição de estado para a operadora e o devedor, com recuperação de falhas e conciliação manual documentadas.
- [ ] Autorizar ativação produtiva e eventual transação real controlada; conferir recebimento e lançamentos antes da liberação geral.

**Saída:** pagamento recebido, validado e lançado corretamente, com rastreabilidade e sem duplicidade.

## 7. Continuidade do produto

- [ ] Retomar as pendências do PLAN-033: resumo diário, aviso de véspera, Copilot conversacional e pré-cadastro, respeitando dependências e gates próprios.
- [ ] Reavaliar a ordem entre essas entregas e Mercado Pago quando o plano de pagamentos estiver definido; nenhuma fase foi cancelada ou declarada concluída aqui.

## Fontes e critério de atualização

Fontes internas: [contexto externo](../../operations/contexto-externo.md), PLAN-034, PLAN-033 e [mapa de retomada](HANDOFF.md).

A documentação oficial descreve URLs HTTPS para notificações e validação de origem por assinatura, conforme a integração. Também orienta consultar a API para obter o recurso notificado. O requisito é um endpoint público alcançável, não especificamente uma VPS; o projeto escolhe usar a VPS já prevista. Referência consultada em 2026-09-08: [Webhooks — Mercado Pago Developers](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/notifications/webhooks). Revalidar o contrato ao escolher a modalidade.

Atualizar cada etapa com data, evidência e responsável. Uma mudança de escopo ou decisão material deve ser registrada na fonte de governança correspondente antes da execução.
