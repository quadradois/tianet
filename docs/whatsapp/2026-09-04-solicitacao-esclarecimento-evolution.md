# Solicitação de esclarecimento — Evolution Go

**Para:** equipe que mantém o Evolution Go (`diamondgreen.com.br`)
**De:** TiaNet
**Data:** 2026-09-04
**Tenant:** `tianet`
**Instância de referência:** `adm_tianet` (`8a8c901f-16f9-4431-b19d-ed69cccc46c0`)

---

# 1. Por que estamos perguntando

Estamos construindo a tela que conecta o WhatsApp dentro da plataforma, e três
decisões de desenho dependem de comportamentos do servidor que **não temos como
observar sem mexer na instância de produção**.

Preferimos perguntar a quem construiu do que descobrir tentando.

**O que já sabemos e não precisa ser repetido:** o contrato em
`CRM_EVOLUTION_CONTRACT.md` está auditado contra o comportamento real e cobre os
três níveis de autenticação, os nomes de evento, o formato de `POST /send/text` e
os bugs conhecidos (`500` com `record not found`, `Qrcode` com Q maiúsculo). As
perguntas abaixo são o que **não** está lá.

Cada pergunta traz **o que faríamos com cada resposta** — se alguma for cara de
responder, diga, e nós medimos em produção com o número do fundador.

---

# 2. Ciclo de vida do QR *(bloqueia a tela agora)*

O contrato §4.2 diz: *"O QR expira sozinho em ~20s e o servidor gera até 5 antes
de reiniciar o ciclo."*

**2.1 — `GET /instance/qr`, chamado repetidamente sem novo `connect`, devolve o QR
ATUAL (que rotacionou), ou o mesmo até alguém chamar `connect` de novo?**

> *Por que importa:* é a diferença entre a tela trocar o QR sozinha (como o
> WhatsApp Web faz) e obrigar o operador a clicar em "gerar novo" a cada 20
> segundos. Se `GET /instance/qr` acompanha a rotação, chamamos só ele.

**2.2 — Qual o intervalo real de rotação, e existe intervalo mínimo recomendado
para consultar `/instance/qr`? Há limite de requisições?**

> *Por que importa:* vamos configurar o intervalo da tela. Preferimos o número de
> vocês a um valor chutado que gere consulta demais.

**2.3 — O que acontece exatamente ao fim do 5º QR?** A instância volta a
`desconectado`? Continua aceitando `GET /instance/qr` (com erro)? Precisa de novo
`POST /instance/connect` para reiniciar o ciclo?

> *Por que importa:* define o que a tela mostra quando a janela acaba — se oferece
> "gerar novo QR", se precisa recomeçar do zero, e qual mensagem é honesta.

**2.4 — Chamar `POST /instance/connect` de novo enquanto um pareamento está
pendente: é seguro? Reinicia o ciclo dos 5? Re-registra o webhook? Causa algum
efeito indesejado?**

> *Por que importa:* é o caminho que evitamos justamente por não saber. Se for
> inofensivo, ele resolveria a renovação sem rota nova do nosso lado.

**2.5 — O evento `QRTimeout` dispara a cada QR que expira, ou só no fim do
ciclo?**

> *Por que importa:* hoje não consumimos webhook (ele aponta para outro serviço),
> mas isso muda o desenho futuro — se o evento for por QR, dá para empurrar o
> código novo em vez de consultar.

---

# 3. `logout` repetido *(decisão nossa apoiada em premissa)*

Registramos numa decisão de arquitetura que desconectar é convergente — repetir
leva ao mesmo estado final. **Isso é premissa nossa, não medição**, e está escrito
como premissa.

**3.1 — `POST /instance/logout` numa instância JÁ desconectada: qual status e
corpo?** É tratado como sucesso, ou retorna erro?

> *Por que importa:* nosso adaptador recusa qualquer resposta que não seja `2xx`.
> Se vocês devolvem erro nesse caso, a segunda chamada falha em vez de convergir,
> e precisamos tratar essa resposta específica como sucesso — do mesmo jeito que
> já fazemos com `record not found` na exclusão.

---

# 4. Deduplicação no envio *(caveat aberto desde 2026-09-02)*

O `POST /send/text` aceita um `id` que enviamos, e a resposta ecoa esse mesmo `id`
em `data.Info.ID` — verificado ao vivo em 2026-08-31.

**4.1 — Se o mesmo `id` for enviado duas vezes, o servidor suprime a segunda
mensagem, ou o destinatário recebe duas vezes?**

> *Por que importa:* é o que decide se um reenvio após timeout é seguro. Hoje
> tratamos todo resultado incerto como "não reenviar, concilia manualmente",
> porque não sabemos. Se vocês deduplicam pelo `id`, podemos reenviar com
> segurança e a conciliação manual deixa de ser necessária. Isso alcança o
> comprovante de empréstimo e o aviso de sobra de pagamento — duplicar um
> comprovante sugere ao devedor que existem dois empréstimos.

**4.2 — Existe janela de tempo para essa deduplicação, se ela existir?**

---

# 5. Estados da instância

**5.1 — Confirmar a leitura de `Connected` e `LoggedIn` durante o pareamento:**
entendemos que, com o QR na tela aguardando leitura, a instância fica
`Connected: true, LoggedIn: false`, e que só `LoggedIn` significa pareado. Está
correto?

> *Por que importa:* é a regra que usamos para dizer "conectado" ao operador. Se
> estiver invertida em algum caso, mostramos estado errado na tela.

---

# 6. O que não estamos pedindo

- Ambiente de teste separado. Sabemos que não existe, e a validação em produção
  com o número do fundador funcionou bem no IMP-352.
- Mudança de comportamento no servidor. Todas as perguntas são sobre o que **já**
  acontece; queremos nos ajustar a ele, não pedir alteração.
- Prazo. Se alguma pergunta for demorada, responda as outras primeiro — a §2 é a
  única que bloqueia trabalho hoje.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 04/09/2026 | Cinco blocos de perguntas que o contrato auditado não cobre, cada uma com o que faríamos com a resposta. A §2 (ciclo do QR) bloqueia a tela de conexão hoje; a §3 sustenta uma premissa declarada em ADR; a §4 é caveat aberto que hoje custa conciliação manual em todo resultado incerto de envio. |
