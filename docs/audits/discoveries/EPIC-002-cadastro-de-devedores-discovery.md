# EPIC-002 — Product Discovery — Cadastro de Devedores

**ID:** EPIC-002

**Tipo:** Artefato de Discovery (engenharia de produto)

**Status:** Em revisão

---

# 1. Objetivo de Negócio

Habilitar o Credor (proprietário da Carteira, FOUNDATION-002 §Credor) a
cadastrar, manter e consultar os **Devedores** da sua operação de crédito
dentro do contexto **Cadastro** (FOUNDATION-009 §5, AMP-001 §4.2), garantindo
identificação única, histórico cadastral preservado e isolamento multi-tenant.

O cadastro de Devedores é o **bloco de construção** de todas as operações
seguintes (Comercial, Contratos, Motor Financeiro — FOUNDATION-009 §6.2 e
AMP-001 §10.1): nenhum Contrato ou Empréstimo existe sem um Devedor
formalizado (DOMAIN-003 RN-002 — todo Contrato pertence exatamente a um
Devedor).

# 2. Valor Entregue ao Usuário

- O Credor registra o Devedor com identificação civil (CPF — pessoa física na
  versão 1, DOMAIN-002 RN-004) e meios de contato;
- A duplicidade de cadastro é impedida pela unicidade do documento dentro da
  Carteira, evitando devedores fantasma e operações sobrepostas;
- O histórico cadastral é preservado e auditável (ADR-002), mesmo após
  inativação — nenhum cadastro é perdido;
- Consultas por ID, documento e listagem paginada permitem operação diária e
  integram sistemas externos;
- Sem esta Feature, Comercial/Contratos não têm a entidade formalizada de
  origem (FOUNDATION-007 §3.2 — Administrar Cadastro).

# 3. Escopo

- Criar Devedor (dados obrigatórios, documento, contatos, estado inicial);
- Validar unicidade do documento dentro da Carteira;
- Consultar Devedor por ID e por documento;
- Listar Devedores com paginação, ordenação e filtros;
- Atualizar dados cadastrais e contatos;
- Inativar e reativar Devedor;
- Consultar histórico cadastral (trilha de auditoria da escrita);
- Vínculo obrigatório do Devedor com a Carteira (e, transitivamente, com o
  Tenant — DOMAIN-019).

# 4. Fora do Escopo

- Operações de crédito (Empréstimos, Parcelas, Pagamentos) — Motor Financeiro
  (EPIC-004/005);
- Contratos de Crédito e formalização — contexto Contratos (EPIC-003);
- Propostas, simulações e análise comercial — contexto Comercial (EPIC-003);
- Autenticação e autorização — IAM (EPIC-006);
- Empresas como Devedor — versão 1 restrita a pessoa física (DOMAIN-002
  RN-004);
- Integrações externas (bureaus de crédito, consultas de CPF, Serasa etc.) —
  fora do MVP (FOUNDATION-008 §4);
- Importação em massa de cadastros;
- Documentos de identidade anexados (fotos, PDFs) — File Storage (pós-MVP).

# 5. Linguagem Ubíqua (termos do contexto Cadastro)

Termos já oficiais (FOUNDATION-002/FOUNDATION-005) e termos do contexto
Cadastro definidos neste Discovery:

| Termo | Definição | Fonte |
|-------|-----------|-------|
| Devedor | Pessoa responsável pelas obrigações financeiras de uma operação de crédito; pertence exatamente a uma Carteira. | FOUNDATION-002 §Devedor; FOUNDATION-005 §3 |
| Pessoa | Indivíduo cadastrado na Carteira; tomador dos empréstimos. Base do Devedor na v1. | DOMAIN-002 |
| Carteira | Aggregate Root do Credit Context; conjunto de operações e Devedores de um Credor. | DOMAIN-001 |
| Documento | Identificação civil oficial do Devedor (CPF na v1), imutável e único por Carteira. | Este Discovery (DOMAIN-022) |
| Contato | Meio de comunicação do Devedor (telefone, e-mail, WhatsApp), tipado, com ciclo de vida próprio. | Este Discovery (DOMAIN-021) |
| Histórico Cadastral | Trilha de todas as alterações do cadastro do Devedor (append-only, ADR-002). | Este Discovery |
| Cadastro Ativo | Estado do Devedor apto a originar operações. | Este Discovery |

Os termos novos (Documento, Contato, Histórico Cadastral) são definidos no
glossário dos documentos DOMAIN do contexto (DOMAIN-020..029) — linguagem
ubíqua local do contexto Cadastro, sem conflito com os termos globais.

# 6. Atores

| Ator | Papel |
|------|-------|
| Credor (via Usuário do Tenant) | Cadastra, consulta, atualiza e inativa Devedores da própria Carteira. |
| Sistema (Comercial/Contratos futuros) | Consome Devedores formalizados como origem de operações. |

Na v1 do MVP, sem IAM operacional (EPIC-006 pendente), os endpoints operam no
contexto autenticado existente do MVP (mesma premissa do EPIC-001 — PLAN-002
§6, FOUNDATION-008). Quando a autorização existir, o acesso será restrito aos
perfis com permissão de escrita/leitura de Cadastro.

# 7. Casos de Uso

- UC-001 — Criar Devedor: informar nome, documento (CPF) e contatos; o sistema
  valida os dados, garante a unicidade do documento na Carteira e cria o
  cadastro em estado Ativo, registrando auditoria;
- UC-002 — Consultar Devedor por ID: obter os dados cadastrais e o estado
  atual a partir do ID (UUID);
- UC-003 — Consultar Devedor por documento: obter o cadastro a partir do CPF
  (dado humano estável, único por Carteira);
- UC-004 — Listar Devedores: relação paginada com ordenação determinística e
  filtros (nome, documento, estado);
- UC-005 — Atualizar dados cadastrais: alterar nome e contatos via PATCH;
  dados imutáveis (documento, vínculo com Carteira) não são alteráveis;
- UC-006 — Inativar Devedor: transição Ativo → Inativo; histórico preservado;
- UC-007 — Reativar Devedor: transição Inativo → Ativo;
- UC-008 — Consultar histórico cadastral: ler a trilha de auditoria das
  alterações do cadastro.

# 8. Regras de Negócio

- RB-001: Todo Devedor pertence exatamente a uma Carteira (DOMAIN-001
  INV-001; materializado como DOMAIN-020 INV-001);
- RB-002: O documento (CPF) é único dentro da Carteira — não podem existir
  dois Devedores ativos ou inativos com o mesmo documento (DOMAIN-024);
- RB-003: O documento é imutável após a criação do cadastro;
- RB-004: Somente pessoa física é cadastrável na versão 1 (DOMAIN-002 RN-004);
- RB-005: Devedor com histórico financeiro nunca é excluído fisicamente —
  apenas inativado (DOMAIN-002 RN-005/RN-006; DOMAIN-025);
- RB-006: A inativação não altera o histórico cadastral nem financeiro;
- RB-007: Devedor inativo não pode originar novas operações (o bloqueio
  efetivo de originação será aplicado no contexto Comercial/Contratos);
- RB-008: Toda escrita no cadastro é registrada em trilha append-only
  (ADR-002); consultas não geram trilha;
- RB-009: O isolamento multi-tenant é garantido pela Carteira (DOMAIN-019):
  nenhum dado de Devedor é acessível fora do Tenant da sua Carteira;
- RB-010: Ao menos um contato válido é obrigatório na criação
  (telefone e/ou e-mail — DOMAIN-021).

# 9. Máquina de Estados

Baseada no ciclo de vida da Pessoa (DOMAIN-002 §4 — Criada/Ativa/Inativa):

```
Criado ──(confirmação do cadastro)──▶ Ativo
Ativo  ──(inativar)─────────────────▶ Inativo
Inativo ──(reativar)────────────────▶ Ativo
```

- **Criado**: estado efêmero durante o processamento do cadastro (análogo ao
  `provisao` do Tenant, PLAN-001 §5);
- **Ativo**: estado final da criação; apto a originar operações;
- **Inativo**: bloqueado para novas operações; histórico preservado;
- Transições inválidas (ex.: reativar um Devedor Ativo) violam invariante e
  retornam erro de estado (padrão 409 `conflito_estado` do EPIC-001, IMP-036).

Nenhuma transição para estado de exclusão existe (RB-005).

# 10. Invariantes

- INV-001: Devedor pertence exatamente a uma Carteira (DOMAIN-001 INV-001);
- INV-002: Documento único por Carteira (RB-002);
- INV-003: Documento imutável (RB-003);
- INV-004: Devedor nunca perde o histórico cadastral/financeiro (RB-005/006);
- INV-005: Transições de estado apenas entre Ativo e Inativo, na ordem da
  máquina de estados (§9);
- INV-006: Nenhum Devedor de um Tenant é acessível por outro Tenant (RB-009).

# 11. Eventos de Domínio

| Evento | Ocorre quando | Consumidores previstos |
|--------|---------------|------------------------|
| Devedor Cadastrado | Cadastro concluído com sucesso | Comercial (originação), Relatórios, Search (futuro) |
| Devedor Atualizado | Dados cadastrais/contatos alterados | Relatórios, Search (futuro) |
| Devedor Inativado | Transição Ativo → Inativo | Comercial, Cobrança (futuro) |
| Devedor Reativado | Transição Inativo → Ativo | Comercial, Cobrança (futuro) |

Os eventos seguem o padrão do domínio (DOMAIN-011..013) e serão materializados
como DOMAIN-026..029. Na v1, sem Event Bus (ADR-005 futuro), são registrados
na trilha de auditoria e publicados no bus interno em memória quando este
existir (AMP-001 §3.1).

# 12. Integrações

- **Interna (obrigatória):** Carteira do Credit Context (vínculo do Devedor);
  Tenant via Carteira (isolamento — DOMAIN-019);
- **Nenhuma integração externa na v1** (FOUNDATION-008 §4 — sem bureaus, sem
  consultas de CPF em terceiros);
- As demais integrações serão consumidoras de eventos (Comercial, Contratos,
  Relatórios — AMP-001 §6.1).

# 13. Riscos

| ID | Risco | Mitigação |
|----|-------|-----------|
| R-01 | Duplicidade de cadastro por variação de formatação do CPF | Normalização do documento (somente dígitos) + constraint UNIQUE por Carteira + service de unicidade (DOMAIN-023) |
| R-02 | Vazamento de dados pessoais (LGPD) | Isolamento por Carteira/Tenant (RB-009), DTO sem dados internos, restrição de exposição |
| R-03 | Inativação bloqueando operações legítimas | Sem efeito retroativo: inativação apenas impede novas operações; operações existentes não são afetadas (RB-007) |
| R-04 | Consulta pesada de listagem degrada performance | Paginação obrigatória com ordenação determinística (padrão EPIC-001 — FEATURE-002) |
| R-05 | Ausência de autenticação no MVP expõe endpoints | Aceito temporariamente (EPIC-006 precede expansão); endpoints revistados quando a autorização existir |
| R-06 | Corrida na criação com o mesmo documento | Constraint UNIQUE + tratamento de conflito de corrida (padrão FEATURE-001 IMP-008/IMP-021) |
| R-07 | Exclusão acidental de cadastro com histórico | Exclusão física proibida por regra (DOMAIN-025) e auditoria de escrita |

# 14. Dependências

- EPIC-001 — Gerenciar Tenant (concluído — fornece Tenant/Carteira);
- DOMAIN-001 — Aggregate Carteira (vínculo obrigatório do Devedor);
- DOMAIN-002 — Entity Pessoa (base do Devedor na v1);
- DOMAIN-019 — BR-004 (Carteira pertence exatamente a um Tenant);
- PRODUCT-002 — Capability Administrar Cadastro (novo, nasce neste Discovery —
  FOUNDATION-009 BR-006/§10.2);
- FOUNDATION-002 — Modelo de Domínio e Linguagem Ubíqua;
- FOUNDATION-005 — Inventário do Domínio;
- FOUNDATION-007 — Product Map (§3.2 Administrar Cadastro);
- FOUNDATION-008 — Escopo do MVP (§3 Cadastro);
- FOUNDATION-009 — Capability Map (contexto Cadastro, EPIC-002);
- ADR-001 — Arquitetura em camadas (Domain puro, Presentation → Application →
  Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação;
- AD-001 — Transação única no MVP (Platform/Credit compartilham a base);
- AD-002 — Idempotency Key (criação de Devedor idempotente);
- AMP-001 — Architecture Master Plan (§4.2 Cadastro; §10.1 item 2);
- ROADMAP-ALIGNMENT-001 — decisão EPIC-002 = Cadastro de Devedores (§5.2,
  §8, §10.1).

# 15. Fronteiras do Bounded Context (Cadastro)

- **Contexto primário:** Cadastro (FOUNDATION-009 §5 — Devedores, histórico
  cadastral, contatos, documentos);
- **Não é Core Domain** (FOUNDATION-009 §5 — Core Domain é o Motor
  Financeiro);
- Nenhum cálculo financeiro ocorre neste contexto (BR-007 — FOUNDATION-009);
- Relação no Context Map (FOUNDATION-009 §6.1): Cadastro consome Platform e
  alimenta Comercial → Contratos → Motor Financeiro;
- O Devedor é Aggregate Root do contexto Cadastro; a Carteira (Credit Context)
  referencia Devedores por ID — DOMAIN-001 INV-001 permanece como invariante
  de referência (todo Devedor pertence a uma Carteira), sem alteração do
  documento aprovado;
- Comunicação cross-context é feita por eventos (DOMAIN-026..029) — sem
  acoplamento direto com downstreams.

# 16. Relação com Tenant

- Devedor → Carteira (1:1, obrigatório) → Tenant (1:1 na v1 — DOMAIN-019);
- O Tenant é a fronteira de isolamento (FOUNDATION-006): todo acesso ao
  Cadastro é mediado pela Carteira do Tenant do usuário autenticado;
- Nenhum Devedor existe fora de uma Carteira, portanto fora de um Tenant;
- A numeração/inventário de Devedores é por Carteira (sem contadores globais).

# 17. Autoavaliação de Consistência

| Verificação | Resultado |
|-------------|-----------|
| Conflito com fontes oficiais (FOUNDATION-001..009, AMP-001, ROADMAP-ALIGNMENT-001, ADRs) | Nenhum — EPIC-002 = Cadastro de Devedores, contexto Cadastro, não Core Domain, sem cálculo financeiro |
| Necessidade de alterar FOUNDATION | Não — termos novos ficam no glossário do contexto (DDD); Devedor já é oficial na Linguagem Ubíqua |
| Necessidade de ADR nova | Não — camadas, auditoria, transação única e idempotência já decididos (ADR-001/002, AD-001/002) |
| Mudança de Bounded Context ou Capability | Não — contexto Cadastro e Capability Administrar Cadastro já mapeados (FOUNDATION-009 §5, FOUNDATION-007 §3.2) |
| Conflito de linguagem ubíqua | Não — termos novos confinados ao contexto; nenhum termo global redefinido |
| Dúvida sobre Core Domain | Não — Motor Financeiro permanece o único Core Domain |
| Decisões irreversíveis | Nenhuma |
| Alinhamento com FOUNDATION-009 (BR-001..BR-008) | BR-001 ✓ (hierarquia), BR-002 ✓ (EPIC ≠ Contexto), BR-003 ✓ (numeração global), BR-004 ✓ (EPIC-002 ligado a PRODUCT-002), BR-005 ✓ (contexto primário Cadastro), BR-006 ✓ (PRODUCT-002 nasce no Discovery), BR-007 ✓ (sem cálculo), BR-008 ✓ (Discovery antes do Product) |

**Conclusão da autoavaliação:** o Discovery é consistente com a governança
congelada. Nenhuma condição de parada (FOUNDATION/ADR/conflito/contexto/
capability/Core Domain/linguagem irreversível) foi atingida. O ciclo segue
para a materialização (Fase B — Product).

---

# User Stories Candidatas

Identificação das histórias necessárias para o EPIC-002 (a materializar na
Fase B):

- FEATURE-005 — Criar Devedor: US-015 (Criar), US-016 (Validar dados
  obrigatórios), US-017 (Validar unicidade do documento), US-018 (Registrar
  contatos), US-019 (Registrar auditoria), US-020 (Confirmar criação);
- FEATURE-006 — Consultar Devedor: US-021 (por ID), US-022 (por documento),
  US-023 (listagem paginada);
- FEATURE-007 — Atualizar Devedor: US-024 (atualizar dados cadastrais e
  contatos);
- FEATURE-008 — Inativar/Reativar Devedor: US-025 (inativar), US-026
  (reativar), US-027 (consultar histórico cadastral).

Critérios de aceitação transversais propostos:

- escrita idempotente (AD-002) e auditada (ADR-002);
- 404 para Devedor inexistente; 409 para documento duplicado e para transição
  de estado inválida; 422 para dados inválidos;
- listagem paginada com ordenação determinística;
- DTO único de resposta (padrão EPIC-001 — RA-012);
- isolamento por Carteira/Tenant em toda consulta.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 0.1.0 | 05/08/2026 | Primeira versão do Discovery do EPIC-002 — Cadastro de Devedores, para revisão arquitetural (ciclo SDD + Agent Loop). |
