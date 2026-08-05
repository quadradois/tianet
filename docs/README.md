# TiaNet — Documentação do Produto

## Propósito

Este diretório contém a documentação oficial da TiaNet. Use este arquivo como ponto de entrada para navegar por todas as camadas documentais.

---

## Estrutura

```
docs/
├── foundation/           # Visão, escopo, princípios, linguagem ubíqua
├── domain/               # Modelo de domínio DDD, organizado por bounded context
│   ├── platform/
│   └── credit/
├── product/              # Product design, organizado por bounded context
│   ├── platform/
│   └── credit/
├── architecture/         # AMP, ADRs, reviews, migration plan
│   ├── amp/
│   ├── adrs/
│   └── reviews/
├── implementation/       # Planos técnicos e backlogs de execução
│   ├── plans/
│   └── backlogs/
├── governance/           # Handoffs, decision requests, processos
│   ├── handoffs/
│   └── decision-requests/
├── audits/               # Auditorias e descobertas
│   ├── audits/
│   └── discoveries/
├── templates/            # Templates para novos documentos
├── assets/               # Diagramas, imagens
└── ux/                   # Wireframes e materiais de UX
```

---

## Como usar

1. **Novo colaborador ou agente:** comece por `foundation/FOUNDATION-001-product-vision.md`.
2. **Entender o domínio:** leia os documentos em `domain/<bounded-context>/`.
3. **Entender o produto:** leia os documentos em `product/<bounded-context>/`.
4. **Decisões arquiteturais:** leia `architecture/adrs/`.
5. **Visão estratégica de longo prazo:** leia `architecture/amp/AMP-001-architecture-master-plan.md`.
6. **Implementar uma feature:** leia `implementation/plans/` e `implementation/backlogs/`.
7. **Criar um novo documento:** use os templates em `templates/`.

---

## IDs e rastreabilidade

Cada documento possui um ID estável no cabeçalho. A localização física pode mudar, mas o ID permanece. Use IDs para referenciar documentos em discussões e implementações.

---

## Validação

Antes de qualquer commit, execute:

```bash
npm run docs:validate
```

---

## Camadas de evolução futura

As seguintes camadas podem ser criadas conforme o produto amadurecer:

- `engineering/` — CI/CD, observability, standards, security
- `operations/` — runbooks e playbooks
- `references/` — reorganização de templates, assets e UX
- `architecture/context-maps/` — mapas de contexto
- `architecture/rfcs/` — propostas formais de mudança
- `index.json` — índice automático dos documentos

---

*Gerado durante o planejamento da migração documental (2026-08-04).*
