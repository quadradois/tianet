# Evidência sanitizada — autenticação OpenAI/Codex Slice E

**Data:** 2026-09-10  
**Escopo:** login real assistido, diagnóstico sem inferência e recuperação após restart  
**Dados de clientes:** nenhum  
**Segredos, e-mail OpenAI, user code e login ID persistidos:** nenhum

## Resultado observado

O proprietário concluiu o device login no domínio oficial da OpenAI. O snapshot
local confirmou `accountConnected=true`. Após diagnóstico explícito, o App Server
0.146.1 informou o plano `prolite`, estado `CONECTADO` e cinco modelos:

- `gpt-5.6-sol` (padrão);
- `gpt-5.6-terra`;
- `gpt-5.6-luna`;
- `gpt-5.5`;
- `gpt-5.3-codex-spark`.

Na observação de `2026-09-10T04:29:01Z`, a OpenAI informou uma janela
`codex_bengalfox` de 300 minutos com 0% usado e uma secundária de 10.080
minutos com 0% usado. Também informou uma janela `codex` de 10.080 minutos com
60% usado. Os instantes de reset permanecem apresentados pela aplicação quando
fornecidos; esta evidência não os interpreta como garantia contratual.

O contêiner do agent foi reiniciado e voltou saudável. Sem novo login, o
snapshot retornou `accountConnected=true`, plano `prolite` e estado `CONECTADO`,
confirmando recuperação pelo volume isolado.

## Ajuste observado na interface

Ao voltar da aba oficial, a tela podia permanecer visualmente em espera embora
o backend já estivesse conectado. O polling foi reforçado para revalidar ao
recuperar foco ou visibilidade, respeitar o mesmo prazo máximo e agrupar eventos
consecutivos. A tela ganhou `Verificar agora`, texto sobre a atualização
automática e confirmação explícita de login, inclusive no estado
`LIMITE_ATINGIDO`.

Lint, typecheck, build, 18 testes focais do componente, o conjunto completo de
100 testes de componente e 6 cenários Playwright desktop/mobile foram aprovados.
A revisão especializada `READ_ONLY` aprovou a correção após exigir deadline nos
handlers, remoção dos listeners e agrupamento dos eventos.

## Selo operacional no shell

A conexão OpenAI saiu de `Mais ferramentas` e passou a aparecer como selo
operacional abaixo do menu, junto ao selo do WhatsApp. O selo apresenta em texto
o estado conhecido, o plano quando conectado e orientações específicas para
conexão, limite atingido, espera, erro ou indisponibilidade. O acesso permanece
protegido pela permissão exata `openai.conexao.ler`.

O snapshot é carregado em um limite assíncrono com fallback `Verificando
conexão`. Uma demora ou falha da integração não bloqueia a renderização das
páginas financeiras. A consulta continua local ao agent, sem diagnóstico nem
chamada à OpenAI durante a navegação.

Foram aprovados 74 testes unitários, 104 testes de componente, lint, typecheck,
build e 6 cenários Playwright desktop/mobile da jornada OpenAI. A revisão
especializada `READ_ONLY` identificou e teve corrigidos o bloqueio potencial do
shell e a orientação de ação incompatível com usuários que possuem somente
permissão de leitura.

Em uma segunda iteração de UI/UX, o selo passou a apresentar o maior percentual
de uso conhecido e uma barra compacta. A página `/app/openai` passou a separar
estado, plano, maior consumo, janelas e modelos em blocos de leitura rápida. O
snapshot local agora inclui `usageSummary` quando existe diagnóstico anterior;
essa leitura não dispara chamadas ao App Server. Percentuais, duração, reinício
e instante observado são apresentados como informação recebida, sem estimar
quantidade de conversas disponível.

## Proteção de dados e limite da prova

A busca automática encontrou zero ocorrências do user code real nos arquivos do
repositório e nos logs do agent. Não houve prompt, inferência, chamada de tool,
uso de dado de cliente, deploy, commit ou push.

O logout local real ficou adiado para preservar a sessão conectada durante a
avaliação do proprietário. Seu contrato e sua jornada com fake já estão
cobertos; a prova real deve ser encerrada com logout local e flag off quando o
proprietário concluir a avaliação.
