# ADR-003: Escopo single-tenant do v1 — um Credor, um Tenant, um usuário

> **Status:** Aceito
> **Data:** 2026-08-31
> **Autor(es):** Arquitetura
> **Revisor(es):** Fundador
> **Aprovação:** Fundador / 2026-08-31
> **Substitui:** —
> **Substituído por:** —

---

## Contexto

O fundador decidiu, e reafirmou por diversas vezes, que a TiaNet atende **um
Credor**, com **um Tenant** e **um usuário**. A decisão consta no handoff de
2026-08-27 §3, e orientou o IMP-363, que concedeu o catálogo inteiro de
permissões no bootstrap justamente porque separar papel administrativo de
operacional só faz sentido com mais de uma pessoa.

A decisão, porém, **vivia apenas num handoff** — registro de sessão, o degrau
mais baixo da hierarquia documental. Acima dela, os documentos canônicos diziam
o contrário:

| Fonte | O que estabelecia |
|---|---|
| `FOUNDATION-006` §2 | *"A plataforma foi concebida para atender múltiplos Credores de forma simultânea."* Status **Aprovado** |
| `AMP-001` §8 | ADR-003 **reservada** para decidir o nível de isolamento multi-tenant |
| `AMP-001` §3.2 | *"Critérios para ADR-003 (evolução do multi-tenant) definidos e monitorados"* como marco de roadmap |
| `AMP-001` §11.1 | *"Multi-tenant Nível 1"* listado como **dívida a pagar** quando os critérios da ADR-003 fossem atingidos |

**A consequência foi operacional, não teórica.** Toda sessão que lia o canônico
concluía — corretamente, dado o que estava escrito — que o produto é
multi-tenant, e reabria a questão. O fundador precisou repetir a mesma decisão
em sessões sucessivas porque o documento aprovado o contradizia.

Esta ADR existe para encerrar isso no nível certo da hierarquia.

### Fatores Relevantes

- **Negócio:** não há segundo Credor previsto. Desenhar, testar e manter
  isolamento entre organizações que não existem é custo sem contrapartida.
- **Técnicos:** o `tenant_id` já permeia domínio, repositórios e queries. Ele
  funciona como **chave de escopo** e continua correto com um único Tenant.
- **Organizacionais:** uma decisão que só vive em handoff é re-litigada a cada
  sessão. Handoff registra estado; ADR decide.

---

## Decisão

**O v1 da TiaNet é single-tenant no escopo de produto: um Credor, um Tenant, um
usuário.** Multi-tenant deixa de ser objetivo, roadmap ou dívida a pagar.

Esta ADR **emite a reserva ADR-003** do `AMP-001` §8. A reserva perguntava
*"quando evoluir o isolamento para schema ou banco separado?"*. A resposta é que
a pergunta **fica sem objeto** enquanto houver um único Credor — e não que se
tenha escolhido um dos níveis.

### Clarificação de 2026-09-01 — "um usuário" é um operador **humano**

Esta ADR foi lida como se proibisse um segundo Principal no IAM. Não proíbe, e a
diferença importa: o desenho **prevê** identidade própria de serviço para o
Copilot, com perfil minimamente privilegiado e revogável que nunca receberá
`comercial.proposta.decidir`.

**Ainda não existe.** O IMP-355 entregou a rota genérica `POST /iam/usuarios`; o
seed e a atribuição do perfil `copilot` ficam para a Fase C, quando houver agente
a quem atribuí-lo. Já existem, e valem também para operadores humanos, a
separação entre submeter e decidir (IMP-360) e o registro de autoria na trilha
(IMP-361).

**Um agente que age precisa ser identificável na trilha.** Dar ao Copilot o
Principal do humano apagaria justamente a distinção que a ADR-002 existe para
preservar.

O que esta ADR decide continua valendo sem alteração: **um Credor, um Tenant, um
operador humano**. "Um usuário" nunca significou "um Principal" — significou que
não há uma segunda *pessoa* operando, e portanto separar papel administrativo de
operacional não faz sentido no v1, que foi a conclusão do IMP-363.

### O que esta decisão NÃO faz

**Não remove `tenant_id` de lugar nenhum.** Esta é a parte mais importante desta
ADR, e a que mais facilmente será mal lida daqui a alguns meses.

O `tenant_id` permanece:

- na modelagem do domínio e no ORM;
- nas queries de escopo dos repositórios;
- na barreira de acesso cross-tenant (US-041), que continua sendo comportamento
  testado e exigido;
- no `Principal` resolvido pela autenticação.

Ele deixa de ser *promessa de produto* e continua sendo *invariante estrutural*.
Arrancá-lo seria refatoração de alto risco, tocando cada agregado e cada query,
**sem nenhum ganho funcional** — o campo não atrapalha, não custa performance
relevante e é a fronteira que impede que um bug de escopo vire vazamento.

Quem ler "não é multi-tenant" e concluir "então posso apagar a coluna" estará
lendo esta ADR ao contrário.

### O que muda nos documentos

| Documento | Mudança |
|---|---|
| `FOUNDATION-006` | Status passa a **Aprovado — escopo SUSPENSO no v1 pela ADR-003**. O conteúdo é preservado como desenho de referência para uma eventual expansão; deixa de descrever o produto atual. A frase de §2 sobre atender múltiplos Credores simultaneamente é corrigida |
| `AMP-001` §8 | ADR-003 marcada como **EMITIDA**, com a nota de escopo diferente da reserva |
| `AMP-001` §3.2 | O marco de roadmap sobre critérios da ADR-003 deixa de existir |
| `AMP-001` §11.1 | "Multi-tenant Nível 1" deixa de ser dívida a pagar e passa a ser decisão de escopo |
| `AMP-001` §13 | O próximo passo "definir critérios para ADR-003" sai |

Documentos que mencionam multi-tenant como **mecanismo de isolamento**
permanecem inalterados e corretos — são a maioria. A distinção que governa:

- **mecanismo** (escopo por `tenant_id`, barrar acesso cross-tenant): correto, permanece;
- **escopo de produto** (atender vários Credores): revogado por esta ADR.

---

## Consequências

### Positivas

- A decisão passa a viver acima do handoff, e para de ser re-litigada.
- Simplifica decisões futuras: qualquer desenho que exija isolamento por
  organização é fora de escopo por padrão, sem discussão caso a caso. A DR-006
  (conexão do WhatsApp) é o primeiro caso a se beneficiar disso.
- O bootstrap conceder o catálogo inteiro (IMP-363) deixa de ser exceção
  pragmática e passa a ser coerente com o escopo declarado.

### Negativas

- `FOUNDATION-006` deixa de descrever o produto e vira desenho de referência.
  Um documento de fundação suspenso é anomalia na hierarquia, mas preferível a
  apagá-lo: se um segundo Credor aparecer, o desenho já existe.
- Reverter esta ADR, no dia em que houver um segundo Credor, exige reabrir
  `FOUNDATION-006` e reavaliar o nível de isolamento — que é exatamente a
  pergunta que a reserva original fazia.

### Guardrail

`scripts/tests/test-adr-003-single-tenant.js`, na cadeia do `docs:test`, verifica
que esta decisão continua declarada nos três documentos e que a afirmação de
escopo multi-tenant não reaparece em documento canônico.

Sem isso, esta ADR é apenas mais um texto que a próxima sessão pode não ler — e
o problema que ela resolve é precisamente esse.

---

## Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.1.0 | 2026-09-01 | Clarificação: "um usuário" é um operador humano. O desenho **prevê** identidade de serviço própria para o Copilot, ainda não provisionada — o IMP-355 entregou a rota genérica, e o perfil `copilot` fica para a Fase C. Nada do que a ADR decide muda; errada estava a leitura de que ela proibiria um segundo Principal. |
| 1.0.0 | 2026-08-31 | Emissão da reserva ADR-003 com escopo diferente do reservado: decide o escopo single-tenant do v1 em vez do nível de isolamento, preserva `tenant_id` como invariante estrutural e suspende o FOUNDATION-006. |
