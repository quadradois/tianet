# Discovery Arquitetural — ADR-003: Estratégia de Evolução do Multi-Tenant

> **Papel:** Arquiteto de Software Principal
> **Data:** 2026-08-03
> **Objetivo:** descobrir se existe maturidade suficiente para formalizar uma ADR sobre evolução do modelo Multi-Tenant
> **Escopo:** análise estratégica; sem criação de ADR, sem alteração de documentos ou código

---

## 1. Estado Atual

### 1.1 Modelo de isolamento

O TiaNet opera hoje com **Multi-Tenancy Nível 1**:

- **Banco único:** PostgreSQL 16.
- **Schema único:** schema público/padrão.
- **Isolamento físico:** nenhum — todos os dados de todos os tenants coexistem no mesmo banco/schema.
- **Isolamento lógico:** via coluna `tenant_id` em todas as tabelas de domínio (`tenant`, `usuario`, `configuracao`, `carteira`, `idempotency_key`, `audit_log`).

### 1.2 Estrutura do Tenant

O `Tenant` é o **Aggregate Root** do Platform Context (`DOMAIN-017`):

- `id` (UUID) — identidade técnica.
- `identificador_institucional` (string, 120 chars) — identificador de negócio, **único globalmente**.
- `nome` — razão social/nome fantasia.
- `estado` — `provisao | ativo | inativo`.
- `criado_em` — timestamp UTC.

### 1.3 Entidades filhas e vinculação

Toda entidade filha carrega `tenant_id` como FK NOT NULL:

- `UsuarioORM.tenant_id` — com índice e constraint `UNIQUE(tenant_id, email)`.
- `ConfiguracaoORM.tenant_id` — com índice e constraint `UNIQUE(tenant_id, chave)`.
- `CarteiraORM.tenant_id` — com índice (FK para `tenant.id`).

A `Carteira` pertence ao Credit Context (`DOMAIN-001`) mas é criada no mesmo fluxo de provisionamento do Tenant, através de ACL (`AD-003` do `PLAN-001`).

### 1.4 Repository

Os repositórios (`SqlAlchemyTenantRepository`, `SqlAlchemyUsuarioRepository`, `SqlAlchemyConfiguracaoRepository`, `SqlAlchemyCarteiraRepository`) recebem uma `Session` injetada. Atualmente:

- Não há raw SQL sem filtro de tenant.
- As queries usam `tenant_id` quando necessário.
- `TenantRepository.find_by_id()` e `find_by_identificador_institucional()` já pressupõem consulta por tenant.
- `find_all()` retorna todos os tenants (uso administrativo da plataforma, não de um tenant).

### 1.5 Application

O `TenantProvisioningService` é o único caso de uso implementado. Ele cria, em uma **transação única** (`AD-001`):

- Tenant;
- Carteira padrão (Credit Context);
- Usuário administrador;
- Configurações padrão;
- Registro de Idempotency-Key;
- Trilha de auditoria (parcialmente fora da transação, em sessão independente).

Isso significa que o provisionamento atravessa **dois Bounded Contexts** dentro do mesmo commit físico.

### 1.6 API

A API expõe:

- `POST /platform/tenants` — criação.
- `GET /platform/tenants/{tenant_id}` — consulta por ID (parcial, já existente).

Não há ainda endpoints de listagem, atualização, inativação ou reativação.

### 1.7 Infraestrutura de persistência

- `database_url()` lê `DATABASE_URL` ou usa default local.
- `get_engine()` e `get_session_factory()` são singletons globais por processo.
- O `UnitOfWork` abre uma sessão a partir da `session_factory` global.
- Alembic gerencia migrations no schema único.

---

## 2. Limites da Arquitetura Atual

### 2.1 Quando o modelo atual deixa de atender?

O modelo **shared database / shared schema** deixa de ser adequado quando alguma das seguintes condições se tornar verdadeira:

1. **Requisitos legais ou regulatórios** exigirem isolamento físico de dados por organização (ex.: setor financeiro, LGPD/GDPR com interpretação restrita, certificações como SOC2).
2. **Clientes enterprise** exigirem database dedicado como condição de contrato.
3. **Volume de dados por tenant** crescer a ponto de comprometer a performance de consultas de outros tenants.
4. **Número de tenants** crescer a ponto de tornar a administração do banco único impraticável (backups, restores, migrations, tuning).
5. **Necessidade de deploy** de releases específicas por tenant ou tier de serviço.

### 2.2 Sintomas que aparecerão primeiro

| Ordem | Sintoma | Causa raiz |
|---|---|---|
| 1 | Lentidão em relatórios administrativos que cruzam grandes tenants | Falta de índices e de particionamento por tenant |
| 2 | Dificuldade para atender requisitos de backup/restore de um único cliente | Schema/banco compartilhado |
| 3 | Preocupações de compliance sobre vazamento cruzado | Isolamento apenas lógico |
| 4 | Impossibilidade de oferecer plano "dedicado" ou "enterprise" | Infraestrutura homogênea |
| 5 | Lock contention ou I/O concentrado em tenants grandes | Recursos compartilhados |

### 2.3 Métricas que indicarão o limite

| Métrica | O que observar | Quando preocupante |
|---|---|---|
| Latência P95/P99 de consultas por tenant | Degradar para > 1s em consultas simples | Sustentado por > 1 semana |
| Tamanho do banco por tenant | Crescimento desproporcional | Um tenant > 30% do total |
| Número de tenants | Crescimento mensal | Sem plano de escalonamento |
| Tickets de compliance/segurança | Mencionam isolamento físico | Qualquer um |
| Tempo de backup/restore | Restore parcial se tornar inviável | > 4h para um tenant |
| Concorrência de escritas | Lock contention mensurável | > 5% de transações afetadas |

**Não definimos valores numéricos fixos** — isso depende de contratos, SLAs e custo operacional. As métricas acima são os indicadores, não triggers automáticos.

---

## 3. Estratégias Possíveis

### 3.1 Shared Database / Shared Schema (atual)

| Aspecto | Descrição |
|---|---|
| **Vantagens** | Simples de implementar, deploy único, migrations simples, menor custo operacional, ideal para MVP. |
| **Desvantagens** | Isolamento apenas lógico, backup/restore por tenant difícil, compliance limitado, risco de vazamento por bugs, tuning global. |
| **Custo de migração** | **Baixo agora, alto depois.** Hoje ainda não há dados de produção; a migração futura exige reescrita de session factory, migrations e testes. |
| **Impacto no código atual** | Mínimo. A única alteração necessária seria garantir que nenhum código acesse tabelas sem `tenant_id`. |

### 3.2 Shared Database / Schema por Tenant

| Aspecto | Descrição |
|---|---|
| **Vantagens** | Melhor isolamento lógico, backups/restores por tenant mais simples, compliance intermediário, ainda compartilha infraestrutura. |
| **Desvantagens** | Complexidade de gerenciamento de schemas, migrations por tenant ou migrations dinâmicas, conexões compartilhadas (não resolve gargalo de I/O), risco de cross-schema leakage se não houver RBAC no banco. |
| **Custo de migração** | **Médio.** Requer alteração na session factory (setar `search_path`), ajustes no ORM para criar tabelas dinamicamente por schema, e refatoração de testes. |
| **Impacto no código atual** | Médio. Repositories e UoW precisam saber qual schema usar. Migrations Alembic precisam de estratégia de execução por tenant. |

### 3.3 Database por Tenant

| Aspecto | Descrição |
|---|---|
| **Vantagens** | Máximo isolamento físico, backup/restore independente, compliance forte, tuning por tenant, possibilidade de tier de serviço. |
| **Desvantagens** | Custo operacional alto, provisionamento de banco por tenant, gestão de conexões e pools, migrations por tenant, complexidade de failover. |
| **Custo de migração** | **Alto.** Requer reescrita da session factory para selecionar database por tenant, sistema de provisionamento de bancos, e migração massiva de dados. |
| **Impacto no código atual** | Alto. Engine/factory global deixa de fazer sentido; UoW precisa de fábrica de conexões por tenant; deploy fica mais complexo. |

---

## 4. Pontos Irreversíveis

Decisões tomadas hoje que dificultarão a migração futura, se não forem gerenciadas:

1. **Engine/factory de sessão global singleton** (`get_engine()`, `get_session_factory()`). Hoje pressupõe um único banco. Tornar-se-á um gargalo arquitetural se múltiplos databases/schemas forem necessários.

2. **Uso de `merge()` indiscriminado nos repositories**. `merge()` realiza SELECT implícito e pode causar comportamento estranho quando houver múltiplas sessions/schemas. Não é irreversível, mas é barato corrigir agora.

3. **Migrations compartilhadas e globais**. Alembic hoje opera no schema único. Se o número de tenants/schemas crescer, a estratégia de migrations precisará ser redesenhada.

4. **Identificador institucional único globalmente**. Hoje `uq_tenant_identificador_institucional` é global. Se houver database/schema por tenant, a unicidade poderia ser localizada; manter global pode ser desnecessário e limitante.

5. **Transação única atravessando Platform e Credit Context**. `AD-001` do `PLAN-001` presume mesmo banco físico. Se os contexts forem separados, a transação única se tornará inviável e exigirá Saga.

6. **Falta de abstração de "tenant scoping"**. Ainda não existe um componente explícito que diga "para este tenant, use este banco/schema". Isso será necessário em qualquer migração.

---

## 5. Impacto na Arquitetura

### 5.1 Domain

Impacto **baixo**. O Domain modela `tenant_id` como identidade do tenant. Desde que `tenant_id` continue existindo, a mudança de nível é um detalhe de infraestrutura. A invariante "todo recurso pertence a um tenant" permanece válida.

### 5.2 Application

Impacto **médio/alto**. O `UnitOfWork` precisará saber qual schema/database usar. O `TenantProvisioningService` — que hoje cria Tenant e Carteira no mesmo commit — precisará de decisão especial se o isolamento físico separar os contexts.

### 5.3 Infrastructure

Impacto **alto**. Session factory, engine, migrations, ORM metadata, repositories e idempotência/auditoria serão afetados. A auditoria, por exemplo, pode permanecer global (plataforma) ou ser replicada por tenant.

### 5.4 API

Impacto **baixo**. Os endpoints continuarão recebendo `tenant_id` na URL ou derivando do token/escopo. A API não precisa saber se o tenant está em schema separado ou banco separado.

### 5.5 Unit of Work

Impacto **alto**. O UoW atual abre uma sessão da factory global. Em um modelo multi-database, a UoW precisa de uma factory parametrizada por tenant.

### 5.6 Auditoria

Impacto **médio**. A `audit_log` pode continuar global (eventos de plataforma) ou ser particionada por tenant. A decisão afeta compliance e performance.

### 5.7 Idempotência

Impacto **médio**. A `idempotency_key` é global hoje. Se o isolamento aumentar, a chave pode passar a ser única por tenant ou por escopo. Isso muda constraints e lógica de conflito.

### 5.8 Testes

Impacto **médio**. Testes de integração precisarão validar isolamento real entre tenants (múltiplos schemas/databases). Isso aumenta a complexidade do setup de testes.

### 5.9 Deploy

Impacto **alto**. Database por tenant exige orquestração de provisionamento de bancos. Schema por tenant exige gerenciamento de migrations dinâmicas. Shared schema exige apenas o deploy atual.

---

## 6. Critérios Objetivos para Mudança de Nível

Não inventamos triggers numéricos. Os critérios objetivos são:

1. **Requisitos legais/regulatórios:** quando um cliente ou regulador exigir isolamento físico de dados.
2. **Contratos comerciais:** quando um tier de serviço (ex.: "enterprise") incluir database/schema dedicado.
3. **Performance:** quando a latência ou throughput de um tenant degradar a experiência de outros, e o tuning do schema compartilhado não resolver.
4. **Operação:** quando backup/restore, tuning ou migrations do banco único se tornarem inviáveis.
5. **Segurança:** quando a interpretação de compliance exigir que vazamentos cruzados sejam fisicamente impossíveis, não apenas logicamente.
6. **Custo:** quando o custo de infraestrutura dedicada por tenant for menor que o custo de manter isolamento lógico em escala.

A **combinação** desses critérios, e não um único número, deve motivar a mudança.

---

## 7. Preparações de Baixo Custo

Ações que podem ser tomadas agora, sem impacto funcional, para reduzir drasticamente o custo de uma futura migração:

1. **Manter `tenant_id` como única coluna de isolamento.** Já é assim. Não adicionar outras formas de filtro.

2. **Nunca acessar tabelas diretamente sem `tenant_id`.** Sempre usar repositories. Isso evita que queries sem escopo se multipliquem.

3. **Evitar raw SQL e stored procedures.** Favorecer SQLAlchemy ORM/repositories para que o mecanismo de scoping possa ser interceptado no futuro.

4. **Parametrizar a criação de sessão.** Hoje `get_session_factory()` é global. Preparar a injeção de `session_factory` já está parcialmente feito (UoW recebe callable). Não reforçar mais globals.

5. **Não hardcodear schema ou database.** Garantir que migrations e ORM não dependam de nome de schema específico.

6. **Tornar migrations idempotentes e reversíveis.** Facilita execução por tenant no futuro.

7. **Documentar critérios de evolução.** Mesmo sem formalizar ADR, registrar os critérios objetivos para que a decisão futura seja baseada em dados, não em pressão.

8. **Evitar `merge()` para INSERT.** Substituir por `add()`/update explícito reduz dependência de estado da sessão, facilitando multi-tenancy.

9. **Manter auditoria e idempotência como abstrações independentes.** Se um dia forem globais ou por tenant, a mudança será localizada.

10. **Testar isolamento lógico de forma rigorosa.** Testes que garantem que tenant A não vê dados de tenant B preparam o terreno para testar isolamento físico depois.

---

## 8. Conclusão

## A — Ainda NÃO existe decisão suficiente.

**Não criar ADR-003 neste momento.**

### Justificativa técnica

1. **O modelo atual é adequado para o MVP.** Shared database/shared schema com `tenant_id` é a escolha correta para um produto no estágio de validação de mercado, com poucos tenants e sem requisitos de isolamento físico.

2. **Não há dados operacionais de produção.** Sem métricas reais de número de tenants, volume de dados, latência ou requisitos de compliance, qualquer decisão sobre shared schema vs. schema por tenant vs. database por tenant seria **especulativa**.

3. **Os critérios objetivos de mudança ainda não são acionáveis.** Sabemos *quais* critérios observar (compliance, performance, contratos, operação), mas nenhum deles está próximo de ser ativado.

4. **Não há alternativa claramente vencedora.** Cada estratégia tem trade-offs significativos e a escolha depende de informações que ainda não existem (modelo de negócio, tiers de serviço, regulamentação).

5. **Formalizar uma ADR agora seria prematuro e potencialmente prejudicial.** Uma ADR-003 criada hoje teria que ser revisada ou substituída em poucos meses, reduzindo a credibilidade do processo de decisão arquitetural.

### O que fazer em vez de criar a ADR-003

- Aplicar as **preparações de baixo custo** listadas na seção 7.
- Monitorar as **métricas da seção 2.3** assim que o sistema entrar em produção.
- Reavaliar a necessidade da ADR-003 quando **pelo menos um** dos critérios da seção 6 se tornar concreto.
- Manter este Discovery como referência para futura ADR, quando houver maturidade.

### Previsão

A ADR-003 se tornará necessária quando o produto atingir um dos seguintes marcos:

- Primeiro cliente enterprise exigindo isolamento físico;
- Primeiro requisito regulatório específico sobre isolamento;
- Degradação de performance atribuída a multi-tenancy compartilhado;
- Necessidade de oferecer tiers de serviço com infraestrutura diferenciada.

Até lá, **o modelo atual deve permanecer** e a energia arquitetural deve ser direcionada para a implementação das FEATURE-002/003/004, CI/CD, observabilidade e autenticação.
