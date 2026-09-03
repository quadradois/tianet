# SPEC-004 — Regras normativas do código

**Versão:** 1.0.0
**Status:** Aprovado
**Data:** 2026-09-03
**Autor:** Engenharia
**Aprovação:** Fundador / 2026-09-03

---

# 1. Objetivo

Versionar as regras que **o código deve obedecer**, separando-as da configuração
de ambiente do executor.

## 1.1 Por que este documento existe

O `.gitignore` diz, na linha que ignora `/CLAUDE.md`:

> *"Configuração específica de agentes — pertence ao ambiente do executor, não ao
> produto. Conhecimento reutilizável vai para `docs/governance/agents/`."*

**A política é correta. O destino nunca foi construído.** `docs/governance/agents/`
não existia até este documento, então as regras normativas do produto ficaram, por
omissão, dentro de um arquivo declarado como sendo do ambiente — invisível para
qualquer clone limpo e para qualquer revisor que não estivesse naquela máquina.

O custo apareceu em 2026-09-03: uma rodada de review classificou como
**bloqueante** a violação da regra 3, lendo-a de um arquivo que o repositório não
carrega. A decisão correta estava registrada, mas num plano de execução — e a
correção da regra, se fosse feita no `CLAUDE.md`, teria sido conserto local que
não viajaria para lugar nenhum.

## 1.2 O que fica de fora

**Continua no `/CLAUDE.md`, ignorado, e é onde deve estar:** comandos de
desenvolvimento, protocolo de abertura de sessão, caminhos de máquina, e
qualquer coisa que descreva *como o executor trabalha* em vez de *o que o código
deve ser*.

A distinção é essa: **se um revisor precisa citar, é norma e mora aqui. Se só o
executor precisa saber, é ambiente e mora lá.**

---

# 2. As regras

### 1. Domain não importa framework

O Domain usa apenas stdlib — `dataclasses`, `enum`, `uuid`, `datetime`. Nunca
FastAPI, SQLAlchemy ou Pydantic (ADR-001).

### 2. Repositório não commita

Repositórios fazem `merge`/`flush`. O `commit` pertence ao UnitOfWork da
Application. Um repositório que commita tira da Application a única coisa que ela
controla: o limite da transação.

### 3. `Idempotency-Key` obrigatória em escrita

Header `Idempotency-Key` em todo `POST`/`PATCH` de escrita, registrado na mesma
transação.

> **Exceção, e ela é fechada:** três operações da conexão de WhatsApp estão
> isentas pela
> [ADR-019](../../architecture/adrs/ADR-019-isencao-de-idempotency-key-nas-escritas-da-conexao-de-whatsapp.md).
> **Sair desta regra exige ADR**, não justificativa em plano de execução — foi
> exatamente essa distinção que fez quatro rodadas de review reabrirem a mesma
> pergunta.

### 4. Auditoria append-only

Eventos de início, falha e rollback persistem em **sessão independente**, que
sobrevive ao rollback da transação (ADR-002).

O evento é uma **afirmação sobre o mundo**, não um log, e numa trilha append-only
ele não se retira. Daí os três vocabulários: **rollback** (o estado voltou),
**divergência** (o efeito externo ficou), **falha** (deu errado, sem afirmar
estado). Escrever `rollback_aplicado` onde sobrou estado é mentira permanente.

### 5. DTO único por recurso

A Presentation nunca devolve Aggregate (RA-012). Um DTO por recurso —
`TenantResponse`, `DevedorResponse`.

**E o DTO não carrega o que custa caro para montar.** Um campo cujo valor exige
chamada externa não pertence a uma rota de polling: o QR de pareamento saiu do
`GET` da conexão de WhatsApp porque cada consulta ia buscá-lo no provedor, e a
consulta é a rota mais chamada do recurso.

### 6. Exceção de domínio identificável

**Violação de invariante carrega o código na exceção** — `ViolacaoInvarianteError`
com `INV-xxx` / `RN-xxx`. Existem muitas, cada uma diz uma coisa diferente, e quem
consome precisa distinguir qual regra caiu.

**Erro de "não encontrado" não carrega**: o código estável é do **contrato HTTP**
(`recurso_nao_encontrado`), emitido pelo handler. Todas colapsam para a mesma
resposta de propósito — distinguir *o que* não foi encontrado, através da
fronteira, vazaria existência.

Convenção formalizada em 2026-09-03 no docstring de
`src/emprestimo/domain/common/errors.py`, depois de um review cobrar código numa
exceção que já seguia a convenção real do repositório. A convenção é que estava
implícita.

### 7. Teste de domínio cobre a violação, não só o caminho feliz

Testes unitários de domínio exercitam invariantes **e violações intencionais**
(`ViolacaoInvarianteError`).

**Guardrail conta o efeito, não o campo.** Um teste que verifica campo nulo não
prova que a chamada não aconteceu; um que conta a chamada, sim. E o cenário tem
de ser aquele em que o defeito é possível — verificar ausência de QR numa conexão
inexistente passaria com a falha de volta.

### 8. Migration é aditiva

Apenas aditivas, com `downgrade` reversível (drop do que foi acrescentado).
Criar com `alembic revision -m` **manual** — nunca autogenerate cego.

### 9. Português (Pt-Br)

Respostas, explicações, comentários no código e documentação em português
brasileiro.

---

# 3. Como esta lista muda

Emendar uma regra aqui é mudança de governança: **PR próprio**, e ADR quando a
mudança criar exceção a uma regra existente (regra 3 é o precedente).

Adicionar regra nova pede evidência — de preferência um defeito real que a regra
teria impedido. Regra sem incidente que a motive vira cerimônia, e cerimônia é
ignorada na primeira pressa.

---

# 4. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 03/09/2026 | Regras extraídas do `/CLAUDE.md` para o diretório que o próprio `.gitignore` designava e que nunca fora criado. Não é reversão daquela decisão: é a execução dela. As regras 3, 5, 6 e 7 incorporam o que o ciclo do IMP-368 ensinou — a exceção da regra 3 exige ADR, o DTO não carrega campo que custa chamada externa, o código estável do "não encontrado" é do contrato HTTP, e guardrail conta efeito e não campo. Corrigida de passagem a lista numerada, que no arquivo de origem tinha uma seção inteira enfiada entre a regra 1 e a 2. |
