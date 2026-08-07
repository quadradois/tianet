# ADR-018: Identidade Externa do Aggregate Devedor

> **Status:** Aceito
> **Data:** 2026-08-07
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura
> **Aprovação:** Arquitetura / 2026-08-07
> **Substitui:** —
> **Substituído por:** —

---

## Contexto

Durante a execução do EPIC-002 (Cadastro de Devedores) constatou-se divergência
entre quatro fontes quanto ao endereçamento HTTP do Devedor:

| Fonte | O que estabelece |
|---|---|
| DOMAIN-020 §15 | O Devedor é **Aggregate Root** do contexto Cadastro |
| DOMAIN-001 §114, §156 | A Carteira é a **fronteira de consistência**; `Carteira *-- Devedor` (composição) |
| PLAN-003 §6 | Endpoints **aninhados** sob `/carteiras/{carteira_id}` |
| PLAN-003-EXEC (IMP-058/059) | Endpoints **planos** em `/devedores/{id}` |

A implementação de IMP-056..IMP-059 seguiu o backlog de execução e adotou a
forma plana em cinco das oito operações, resolvendo a divergência por escolha
da Engenharia — o que pressupunha uma definição de identidade que nenhuma fonte
registrava. A divergência foi formalizada na DR-001.

O próprio DOMAIN-020 registrava a ambiguidade em seu §179, descrevendo as duas
leituras sem decidir qual governa o endereçamento externo.

### Fatores Relevantes

- **Técnicos:** o isolamento multi-tenant ainda não existe na camada HTTP; a
  forma do endereçamento determina se ele poderá ser estrutural ou terá de ser
  repetido handler a handler.
- **Negócio:** dado de devedor é dado de cliente do Tenant; vazamento entre
  Tenants é falha de confidencialidade, não defeito funcional.
- **Organizacionais:** duas fontes oficiais em conflito produziram decisão
  implícita na implementação — o processo precisa de fonte única.
- **Temporais:** nenhum cliente externo consome a API; a mudança é livre de
  quebra de contrato agora e deixa de ser depois.

---

## Problema

**Ser Aggregate Root implica ter identidade externa própria na API?**

A questão não é de formato de URL: é de modelagem. A resposta determina se o
Devedor é endereçável de forma independente ou sempre no contexto da Carteira
que o contém.

---

## Decisão

**Decidimos que:** o Devedor **permanece Aggregate Root** do contexto Cadastro,
porém sua **identidade externa é contextualizada por uma Carteira**. A hierarquia
oficial de endereçamento passa a ser:

```
Tenant
    └── Carteira
            └── Devedor
```

Portanto, a API pública oficial é `/credit/carteiras/{carteira_id}/devedores/...`
e **nunca** `/credit/devedores/...` como rota oficial do domínio.

Registram-se explicitamente os dois princípios que sustentam a decisão:

> **Aggregate Root não determina identidade externa da API.**

> **Recursos subordinados podem possuir identidade própria no domínio e ainda
> assim possuir identidade contextualizada externamente.**

### Justificativa

Ser Aggregate Root é uma propriedade da **consistência transacional** interna:
significa que o Devedor protege suas próprias invariantes e é carregado e
persistido como uma unidade. Não é uma afirmação sobre como o recurso é
endereçado por um cliente externo.

A fronteira de consistência do domínio Credit é a Carteira (DOMAIN-001 §114), e
o isolamento entre Tenants se dá **via Carteira** (DOMAIN-020 §76). O
endereçamento externo deve refletir essa fronteira: é ela que governa quem pode
ver o quê.

### Consequência operacional: contrato de erro

Quando o Devedor existe mas pertence a outra Carteira, a API responde
**404 `devedor_nao_encontrado`** — o mesmo código de um ID inexistente.

A indistinguibilidade é **intencional**: responder algo diferente confirmaria a
existência do identificador em outra Carteira, vazando informação através da
fronteira que esta decisão pretende reforçar. O código já está previsto no
PLAN-003 §106; nenhum código novo é introduzido.

---

## Alternativas Consideradas

| Opção | Descrição | Prós | Contras | Por que não escolhida |
|-------|-----------|------|---------|----------------------|
| A — Identidade própria (rotas planas) | `/devedores/{id}` para operações por ID | URLs curtas; alinha a leitura literal de DOMAIN-020 §15 | Autorização multi-tenant precisa ser repetida em cada handler; rota esquecida vira vazamento; impossível distinguir `carteira_nao_encontrada` | Transfere uma garantia de confidencialidade para disciplina de implementação |
| B — Híbrido (estado implementado) | Criação/listagem aninhadas; operações por ID planas | Nenhuma alteração de código | Mantém duas convenções sem critério declarado; herda as fragilidades da opção A | Divergência não resolvida, apenas normalizada |
| C — Identidade contextualizada (escolhida) | Todas as operações sob `/carteiras/{carteira_id}/devedores` | Fronteira de autorização explícita na URL; verificável em ponto único; coerente com DOMAIN-001 §114 | URLs mais longas; exige validação de pertinência; leitura adicional nas escritas | — |

---

## Consequências

### Positivas

- A Carteira passa a estar presente em toda requisição de Devedor, tornando a
  futura verificação "este Tenant é dono desta Carteira?" possível **antes** do
  acesso ao dado, em um único ponto de interceptação.
- Elimina a divergência entre PLAN-003 e PLAN-003-EXEC, que era a causa raiz da
  decisão implícita tomada na implementação.
- O contrato de erro passa a ser uniforme e não vazante através da fronteira de
  Carteira.

### Negativas / Riscos

- A URL passa a admitir par inconsistente (Carteira A + Devedor da Carteira B).
  *Mitigação: validação de pertinência obrigatória e **centralizada** em uma
  dependência única de rota, nunca duplicada nos handlers.*
- Operações de escrita passam a exigir uma leitura adicional do Devedor para
  validar a pertinência antes de executar o caso de uso.
  *Mitigação: custo aceito conscientemente; é inerente ao aninhamento e
  proporcional à garantia obtida.*
- URLs mais longas para clientes que já conhecem o `devedor_id`.
  *Mitigação: nenhum cliente externo consome a API hoje.*

### Neutras / Trade-offs

- Caso o Devedor venha a ser referenciado por outros contextos (Contrato,
  Cobrança), a questão da identidade externa deverá ser reavaliada — esta ADR
  decide o endereçamento **no contexto Cadastro**, não veta rotas de resolução
  em contextos futuros.
- A decisão não implementa autorização; apenas torna sua implementação futura
  estrutural.

---

## Impactos

| Artefato | Impacto |
|---|---|
| DOMAIN-020 §179 | Ambiguidade eliminada: Aggregate Root mantido, identidade externa atribuída à Carteira |
| PLAN-003 §6 | Confirmado como forma oficial (já estava aninhado) |
| PLAN-003-EXEC IMP-058/059 | Corrigido de plano para aninhado |
| `presentation/api/devedores_routes.py` | Cinco rotas migradas; validação de pertinência centralizada |
| Testes HTTP e de integração | Atualizados para o contrato aninhado |
| DR-001 | Resolvida por esta ADR |

**Fora do escopo desta decisão:** autenticação, autorização, middleware
multi-tenant, IAM, Saga, eventos, CQRS e novos casos de uso.

---

## Evolução Esperada

A validação de pertinência atualmente ocorre na camada Presentation, por meio da
resolução do recurso associado à Carteira (`get_devedor_da_carteira`). Quando a
arquitetura incorporar autenticação, autorização e filtros multi-tenant na camada
de persistência, essa validação poderá ser absorvida pelo repositório ou pela
infraestrutura, preservando integralmente o contrato definido por esta ADR.

Concretamente, com o Tenant e a Carteira disponíveis a partir do token de sessão,
a consulta poderá filtrar na origem — `WHERE id = ? AND carteira_id = ?` — em vez
de carregar o Devedor e comparar depois. A leitura adicional registrada em
*Consequências / Negativas* deixa de existir, sem que nada mude para o cliente da
API: mesmo endereçamento, mesmo `404 devedor_nao_encontrado`, mesma
indistinguibilidade.

Registra-se, portanto, que:

- a implementação atual **não é dívida técnica**: é a forma correta de materializar
  esta decisão na ausência de autenticação;
- a evolução é **prevista**, não corretiva, e depende da ADR-004 (IAM) e da ADR-003
  (nível de isolamento multi-tenant);
- o **contrato desta ADR permanece inalterado** em qualquer dos cenários — o que
  muda é apenas a camada onde a pertinência é verificada, nunca o seu efeito
  observável.

---

## Validação e Revisão

- **Critério de Aceitação da Decisão:** nenhuma rota oficial de Devedor fora de
  `/credit/carteiras/{carteira_id}/devedores`; validação de pertinência em ponto
  único; suíte verde.
- **Data de Revisão Prevista:** quando o Devedor for referenciado por um segundo
  Bounded Context, ou na entrada da ADR-004 (IAM).
- **Responsável pela Revisão:** Arquitetura.

---

## Referências

- DOMAIN-001 — Aggregate Carteira (§114 fronteira de consistência, §156 composição)
- DOMAIN-020 — Aggregate Devedor (§15 Aggregate Root, §76 isolamento via Carteira, §179)
- PLAN-003 — EPIC-002 Cadastro de Devedores (§6 API, §106 padrões de erro)
- PLAN-003-EXEC — Backlog de Execução (IMP-056..IMP-059)
- DR-001 — Identidade externa do Devedor (Decision Request que originou esta ADR)
- ADR-002 — Auditoria Independente da Transação
- AMP-001 §354 — tabela de ADRs previstas (ADR-017 reservada a Billing; por isso
  esta decisão recebeu o identificador ADR-018)

---

## Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Decisão registrada — identidade externa do Devedor contextualizada por Carteira. |
| 1.1.0 | 07/08/2026 | Seção "Evolução Esperada" — absorção futura da validação de pertinência pela infraestrutura (TASK-089A, revisão arquitetural). |
