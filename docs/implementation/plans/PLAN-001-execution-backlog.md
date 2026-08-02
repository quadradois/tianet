# PLAN-001-EXEC — Backlog de Execução da FEATURE-001 (Criar Tenant)

**ID:** PLAN-001-EXEC

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Contexto

Este documento decompõe o PLAN-001 em um backlog técnico executável para a FEATURE-001 — Criar Tenant.

É a fonte oficial para execução: a implementação deverá ocorrer na ordem definida aqui, permitindo rastreabilidade entre Product → Implementation → Código.

Nenhum código será criado por este documento; ele apenas organiza e detalha o trabalho.

---

# 2. Referências

- PLAN-001 — Plano Técnico da FEATURE-001 (inclui AD-001 — transação única no MVP e AD-002 — Idempotency Key);
- FEATURE-001 — Criar Tenant;
- EPIC-001 — Gerenciar Tenant;
- US-001 — Criar Tenant;
- DOMAIN-017 — Aggregate Tenant; DOMAIN-018 — Entity Usuário; DOMAIN-001 — Aggregate Carteira; DOMAIN-019 — BR-004;
- FOUNDATION-006 — Arquitetura Multi-Tenant; FOUNDATION-008 — Escopo Oficial do MVP.

---

# 3. Infraestrutura

## IMP-001 — Criar Aggregate Tenant

- **Objetivo:** criar o Aggregate Root Tenant conforme DOMAIN-017 (identidade da organização, estado operacional, entidades filhas Usuário e Carteira);
- **Componentes afetados:** Platform Context (modelo de domínio), Tenant;
- **Dependências:** PLAN-001, DOMAIN-017;
- **Critério de conclusão:** agregado implementado com identidade estável e estado inicial definido (Provisão), sem regras financeiras.

## IMP-002 — Criar Entity Usuário

- **Objetivo:** criar a Entity Usuário conforme DOMAIN-018, pertencente ao Aggregate Tenant;
- **Componentes afetados:** Platform Context, Usuário;
- **Dependências:** IMP-001, DOMAIN-018;
- **Critério de conclusão:** entidade criada com vínculo obrigatório ao Tenant (INV-001) e suporte ao ciclo de vida Convidado/Ativo/Inativo/Removido.

## IMP-003 — Criar Entity Configuração

- **Objetivo:** criar a Entity Configuração (parâmetros específicos do Tenant — FOUNDATION-002 §Configuração);
- **Componentes afetados:** Platform Context, Configuração;
- **Dependências:** IMP-001, FOUNDATION-002;
- **Critério de conclusão:** entidade criada com vínculo obrigatório ao Tenant e estrutura para parâmetros iniciais.

## IMP-004 — Criar Repository Tenant

- **Objetivo:** criar o repositório de persistência do Tenant;
- **Componentes afetados:** persistência (Platform Context), Tenant;
- **Dependências:** IMP-001;
- **Critério de conclusão:** operações CRUD básicas disponíveis e constraint UNIQUE do identificador institucional aplicada na base.

## IMP-005 — Criar Repository Usuário

- **Objetivo:** criar o repositório de persistência do Usuário;
- **Componentes afetados:** persistência (Platform Context), Usuário;
- **Dependências:** IMP-002, IMP-004;
- **Critério de conclusão:** persistência disponível com FK obrigatória para o Tenant.

## IMP-006 — Criar Repository Configuração

- **Objetivo:** criar o repositório de persistência das Configurações;
- **Componentes afetados:** persistência (Platform Context), Configuração;
- **Dependências:** IMP-003, IMP-004;
- **Critério de conclusão:** persistência disponível com FK obrigatória para o Tenant.

## IMP-007 — Criar Repository Carteira

- **Objetivo:** criar o repositório de persistência da Carteira no Credit Context;
- **Componentes afetados:** persistência (Credit Context), Carteira;
- **Dependências:** IMP-001, DOMAIN-001, DOMAIN-019;
- **Critério de conclusão:** persistência disponível com FK NOT NULL para o Tenant (BR-004 — nenhuma Carteira sem Tenant).

---

# 4. Domínio

## IMP-008 — Implementar validação de unicidade

- **Objetivo:** garantir que a organização não exista antes do provisionamento (UC-002);
- **Componentes afetados:** Platform Context, Tenant;
- **Dependências:** IMP-004, AD-002;
- **Critério de conclusão:** consulta de unicidade pelo identificador institucional implementada e violação de constraint em corrida tratada (retorno de conflito, sem exceção genérica).

## IMP-009 — Implementar invariantes do Aggregate Tenant

- **Objetivo:** implementar as invariantes DOMAIN-017 INV-001..005 (vínculo obrigatório de Usuário e Carteira, ausência de compartilhamento, limite de 1 Carteira na v1);
- **Componentes afetados:** Platform Context, Tenant;
- **Dependências:** IMP-001, DOMAIN-017, DOMAIN-019;
- **Critério de conclusão:** estados inválidos bloqueados por violação de invariante; nenhuma Carteira/Usuário órfão ou compartilhado.

## IMP-010 — Implementar criação da Carteira padrão

- **Objetivo:** criar a Carteira padrão do Tenant via Credit Context (UC-003);
- **Componentes afetados:** Platform Context (ACL), Credit Context, Carteira;
- **Dependências:** IMP-007, IMP-009, DOMAIN-001, BR-004;
- **Critério de conclusão:** Carteira criada e vinculada ao Tenant dentro do mesmo fluxo de provisionamento.

## IMP-011 — Implementar criação do Usuário Administrador

- **Objetivo:** criar o primeiro Usuário Administrador e associá-lo ao Tenant (UC-004);
- **Componentes afetados:** Platform Context, Usuário;
- **Dependências:** IMP-002, IMP-005, IMP-009, DOMAIN-018 RN-001/RN-002;
- **Critério de conclusão:** Usuário criado com perfil Administrador mínimo, vinculado ao Tenant, sem fluxo de autenticação.

## IMP-012 — Implementar inicialização das Configurações

- **Objetivo:** provisionar as configurações padrão do Tenant (UC-005);
- **Componentes afetados:** Platform Context, Configuração;
- **Dependências:** IMP-006, IMP-009;
- **Critério de conclusão:** parâmetros iniciais persistidos e associados ao Tenant.

---

# 5. Aplicação

## IMP-013 — Implementar TenantProvisioningService

- **Objetivo:** orquestrar o provisionamento completo (UC-001..UC-007): validação → unicidade → Carteira → Usuário → Configurações → confirmação;
- **Componentes afetados:** camada de aplicação, Platform/Credit Context;
- **Dependências:** IMP-008..IMP-012;
- **Critério de conclusão:** fluxo executado na ordem definida e estado operacional final (Ativo) retornado ao fim.

## IMP-014 — Implementar transação única (AD-001)

- **Objetivo:** executar o provisionamento em transação única enquanto os contextos compartilham a base;
- **Componentes afetados:** camada de aplicação, persistência;
- **Dependências:** IMP-013, AD-001;
- **Critério de conclusão:** qualquer falha em qualquer passo gera rollback completo, sem estados parciais visíveis.

## IMP-015 — Implementar Idempotency-Key (AD-002)

- **Objetivo:** impedir provisionamento duplicado via Idempotency Key com constraint único;
- **Componentes afetados:** camada de aplicação, persistência, API;
- **Dependências:** IMP-013, IMP-014, AD-002;
- **Critério de conclusão:** replay com a mesma chave retorna o resultado original sem criar recursos; resultado divergente responde 409.

## IMP-016 — Implementar Auditoria

- **Objetivo:** registrar cada passo do provisionamento em trilha append-only (UC-006, DOMAIN-018 INV-003);
- **Componentes afetados:** camada de aplicação, Auditoria;
- **Dependências:** IMP-013;
- **Critério de conclusão:** trilha completa e imutável (dados validados, carteira criada, usuário criado, configurações aplicadas, confirmação) gravada junto à transação.

---

# 6. API

## IMP-017 — Endpoint POST /platform/tenants

- **Objetivo:** expor a criação de Tenant com header Idempotency-Key (PLAN-001 §6);
- **Componentes afetados:** API REST, TenantProvisioningService;
- **Dependências:** IMP-013..IMP-016;
- **Critério de conclusão:** respostas 201 (provisionado), 409 (conflito de unicidade/idempotência) e 422 (dados inválidos) conforme o plano.

## IMP-018 — Endpoint GET /platform/tenants/{id}

- **Objetivo:** consultar o Tenant e seu estado operacional (suporte à confirmação — UC-007);
- **Componentes afetados:** API REST, Tenant;
- **Dependências:** IMP-013;
- **Critério de conclusão:** retorna o Tenant solicitado com estado atual; 404 para ID inexistente.

---

# 7. Testes

## IMP-019 — Testes unitários

- **Objetivo:** cobrir invariantes e validações de domínio (unicidade, vínculos, estado inicial, RN-002);
- **Componentes afetados:** Platform/Credit Context (domínio);
- **Dependências:** IMP-001..IMP-012;
- **Critério de conclusão:** invariantes e regras cobertas; falhas intencionais verificam bloqueio de estado inválido.

## IMP-020 — Testes de integração

- **Objetivo:** validar o fluxo completo e a atomicidade da transação única (AD-001);
- **Componentes afetados:** camada de aplicação, persistência, Auditoria;
- **Dependências:** IMP-013..IMP-016;
- **Critério de conclusão:** provisionamento completo sem resíduos; falha em qualquer passo não deixa dados parciais.

## IMP-021 — Testes de concorrência

- **Objetivo:** garantir que criação simultânea do mesmo Tenant resulte em um único provisionamento;
- **Componentes afetados:** API, persistência;
- **Dependências:** IMP-017, IMP-008;
- **Critério de conclusão:** apenas uma solicitação vence; as demais recebem 409, sem duplicidade na base.

## IMP-022 — Testes de idempotência

- **Objetivo:** validar o comportamento da Idempotency Key (AD-002);
- **Componentes afetados:** API, camada de aplicação;
- **Dependências:** IMP-017, IMP-015;
- **Critério de conclusão:** replay com a mesma chave retorna o mesmo resultado sem novos recursos; chaves distintas geram provisionamentos independentes.

## IMP-023 — Testes end-to-end

- **Objetivo:** validar o fluxo completo pela API contra os critérios da US-001 §2;
- **Componentes afetados:** API, TenantProvisioningService, persistência;
- **Dependências:** IMP-017, IMP-018, IMP-020;
- **Critério de conclusão:** todos os 10 critérios de aceitação da US-001 cobertos por cenários E2E passando.

---

# 8. Ordem de Execução

A implementação segue a sequência IMP-001 → IMP-023, consistente com a ordem do PLAN-001 §8:

1. Domínio e persistência: IMP-001..IMP-012;
2. Serviço de provisionamento e regras de consistência: IMP-013..IMP-016;
3. API: IMP-017..IMP-018;
4. Verificação: IMP-019..IMP-023.

Cada tarefa só inicia com todas as suas dependências concluídas.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Backlog de Execução da FEATURE-001, decompondo o PLAN-001 em 23 tarefas técnicas (IMP-001..IMP-023). |
