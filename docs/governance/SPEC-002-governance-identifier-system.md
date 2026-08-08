# SPEC-002 — Governance Identifier System

**Versão:** 1.1.0
**Status:** Aprovado
**Data:** 2026-08-07
**Autor:** Engenharia (TASK-098)
**Aprovação:** Arquitetura / 2026-08-07 (DA-098-001..007)
**Consolida:** AC-001, AC-002, AC-003, GA-001, GP-001

---

# 1. Objetivo

Formalizar o sistema de identificadores da governança: namespaces oficiais,
gramática, propriedade, unicidade, ciclo de vida, reserva e depreciação — e
criar o **Identifier Registry** como fonte única de emissão, de modo que
múltiplos executores (pessoas ou agentes) possam trabalhar em paralelo sem
depender de disciplina individual para evitar colisões.

Origem: durante a TASK-096/TASK-097 duas colisões de `TASK` chegaram ao ponto de
bloquear a publicação, e o comando AC-001 foi emitido sob um identificador
(`DA-001`) já pertencente a outro namespace. Ambos os incidentes têm a mesma
causa: **não existe registro do que já foi emitido**.

---

# 2. Inventário levantado (evidência)

O desenho abaixo parte do estado real do repositório, não de suposição. Foram
encontrados **24 namespaces distintos** em uso — bem mais que os 14 previstos na
determinação inicial.

## 2.1 Namespaces com documento próprio

| Namespace | Docs | Maior nº | Onde vive |
|---|---|---|---|
| DOMAIN | 29 | 029 | `docs/domain/**` |
| US | 20 | 027 | `docs/product/**/user-stories/` |
| FEATURE | 11 | 008 | `docs/product/**/features/` |
| FOUNDATION | 9 | 009 | `docs/foundation/` |
| PLAN | 6 | 004 | `docs/implementation/{plans,backlogs}/` |
| EPIC | 3 | 007 | `docs/product/**/epics/` |
| ADR | 3 | 018 | `docs/architecture/adrs/` |
| PRODUCT | 2 | 004 | `docs/product/**/capabilities/` |
| SPEC | 1 | 001 | `docs/governance/` |
| AMP | 1 | — | `docs/architecture/amp/` |
| TASK | 1 | — | (ver §2.3) |

## 2.2 Namespaces sem documento próprio (identificam itens *dentro* de documentos)

`IMP` (369 citações), `RN` (112), `INV` (95), `AD` (73), `BR` (62), `DA` (58),
`RB` (57), `UC` (52), `CC` (17), `RA` (15), `ALP` (13), `CP` (11), `CF` (10),
`CA` (9), `VO` (7), `VAL` (7), `GT` (7), `GF` (6), `GD` (4), `GA` (4), `PD` (2),
`AG` (2), `ENT` (1), `DR` (1).

Estes **não têm arquivo** — são âncoras internas (uma invariante, uma regra de
negócio, um item de backlog). Tratá-los como o Registry trata `ADR` produziria
falso erro em massa.

## 2.3 Três descobertas que alteram o desenho proposto

**a) O contador de `TASK` não pode viver só em documentos.**
O maior `TASK` citado em `docs/` é **089**; no histórico Git é **097**. As TASKs
são artefatos operacionais (GP-001) e sua numeração real está nas mensagens de
commit. Um Registry alimentado apenas por documentos emitiria `TASK-090`, que já
existe.

**b) `ADR` tem reservas, e o próximo número livre não é `máximo + 1`.**
Existem 3 arquivos (`ADR-001`, `ADR-002`, `ADR-018`) e **15 números reservados**
em AMP-001 §354 (`ADR-003`..`ADR-017`, cada um com assunto atribuído). Foi
exatamente por isso que a decisão de identidade do Devedor recebeu `ADR-018` e
não `ADR-003`. Um Registry que guardasse apenas `{"ADR": 18}` perderia a reserva
e reemitiria números ocupados.

**c) Existe pelo menos um namespace legado.**
`DECISION-001` aparece em 5 documentos como alias de `ADR-001`
([ADR-001:121](../architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md)).
Não é erro de digitação: é nomenclatura anterior ainda referenciada. O sistema
precisa de estado **DEPRECATED**, não apenas ativo/inexistente.

---

# 3. Gramática oficial (AC-003)

```
<NAMESPACE>-<NÚMERO>[-<QUALIFICADOR>]
```

- **NAMESPACE**: 2–12 letras maiúsculas, registrado no Registry;
- **NÚMERO**: 3 dígitos com zeros à esquerda (`001`, não `1`);
- **QUALIFICADOR** (opcional): letra maiúscula (`-A`, `-B`) ou palavra minúscula
  (`-fix`, `-hotfix`).

**O qualificador faz parte do identificador** (AC-003). `TASK-092`, `TASK-092-A`
e `TASK-092-B` são três identificadores distintos e **não constituem colisão** —
formam uma *família de execução*.

Exemplos válidos: `ADR-018`, `TASK-097`, `TASK-092-A`, `TASK-049-fix`.

---

# 4. Classes de namespace

A distinção é necessária porque §2.2 mostrou que a maioria dos namespaces não
tem arquivo. Cada classe tem regra de validação própria.

| Classe | Definição | Unicidade verificável por | Exemplos |
|---|---|---|---|
| **DOCUMENT** | um arquivo por identificador | existência do arquivo | ADR, EPIC, FEATURE, US, PLAN, DOMAIN, FOUNDATION, PRODUCT, SPEC, DR |
| **OPERATIONAL** | unidade de execução, sem arquivo | mensagem de commit | TASK |
| **INLINE** | âncora dentro de um documento | documento hospedeiro | IMP, RN, INV, AD, BR, DA, UC, RB, CA… |
| **PRINCIPLE** | princípio/comando de governança | documento que o institui | GA, GP, AC, ALP |

Só as classes **DOCUMENT** e **OPERATIONAL** têm contador no Registry. As demais
são registradas como namespaces válidos, sem sequência — sua unicidade é local
ao documento que as define.

---

# 5. Ciclo de vida e estados

| Estado | Significado | Reemissão permitida? |
|---|---|---|
| `FREE` | nunca emitido, disponível | sim |
| `RESERVED` | atribuído a assunto futuro (ex.: ADR-003..017 no AMP-001) | **não** |
| `ISSUED` | em uso | não |
| `DEPRECATED` | substituído, mas ainda referenciado (ex.: DECISION-001) | **não** |

Identificador emitido **nunca é reciclado**, mesmo que o artefato seja excluído:
referências históricas continuariam apontando para ele.

---

# 6. Registry

## 6.1 Formato

`docs/governance/registry/identifier-registry.json` — JSON, para ser legível por
ferramenta sem parsing de Markdown.

Cada namespace declara os seis campos exigidos por DA-098-005:

```jsonc
{
  "namespaces": {
    "ADR": {
      "prefixo": "ADR",
      "nome": "Architectural Decision Record",
      "classe": "DOCUMENT",
      "governadoPor": "AMP-001",     // DA-098-002: o Registry NÃO calcula ADR
      "regraNumeracao": "reservas do AMP-001 §354",
      "status": "ACTIVE",
      "validador": "docs:validate/identifiers",
      "local": "docs/architecture/adrs/"
    },
    "TASK": {
      "prefixo": "TASK",
      "nome": "Unidade operacional de execução",
      "classe": "OPERATIONAL",
      "governadoPor": "git",         // DA-098-001: o Git é a fonte da verdade
      "regraNumeracao": "max(TASK no histórico Git) + 1",
      "status": "ACTIVE",
      "validador": "docs:validate/identifiers"
    },
    "DECISION": {
      "prefixo": "DECISION",
      "nome": "Decisão arquitetural (nomenclatura anterior a ADR)",
      "classe": "DOCUMENT",
      "governadoPor": "—",
      "regraNumeracao": "não emitir",
      "status": "LEGACY",            // DA-098-004
      "sucessor": "ADR",
      "validador": "docs:validate/identifiers"
    }
  }
}
```

## 6.2 Regra de emissão

A regra depende de `governadoPor`, não de um contador único:

| `governadoPor` | Como obter o próximo |
|---|---|
| `git` | `max(TASK no histórico) + 1` (DA-098-001) |
| `AMP-001` | consultar a tabela de reservas do AMP-001 (DA-098-002) |
| `sequencial` | `ultimo + 1` registrado no próprio Registry |
| `—` (LEGACY) | **não emitir** |

Quando o namespace mantém `ultimo` no Registry, o campo é atualizado **no mesmo
commit** do artefato: dois executores concorrentes passam a conflitar no merge do
Registry, em vez de publicarem IDs colididos.

## 6.3 Limite conhecido

O Registry **não impede** colisão entre dois executores que emitam ao mesmo tempo
antes de qualquer commit; ele a torna **detectável** no merge e no validador.
Prevenção real exigiria emissão centralizada, fora do escopo desta spec.

---

# 7. Extensão do `docs:validate` — família Identifiers (DA-098-007)

O validador passa a ter cinco famílias: `Structural`, `References`, `Contracts`
(SPEC-001), `Governance` e `Identifiers` (esta spec).

| # | Regra | Severidade |
|---|---|---|
| 5.1 | ID de documento duplicado entre arquivos | **ERRO** (já existe) |
| 5.2 | Namespace usado mas ausente do Registry | **ERRO** |
| 5.3 | Novo ID emitido em namespace `LEGACY` | **ERRO** |
| 5.4 | Gramática inválida (`ADR-1` em vez de `ADR-001`) | AVISO |
| 5.5 | Namespace `LEGACY` ainda referenciado por documento vivo | AVISO |
| 5.6 | Registry declara namespace que nenhum documento usa | AVISO |
| 5.7 | Buraco na sequência de namespace `sequencial` | AVISO |

**A regra 5.2 é a que teria impedido o incidente do `DA-001`**: o prefixo já
existia como *Design Assumption*, e usá-lo para *Architectural Command* teria
falhado na validação.

**Regras deliberadamente ausentes.** A v1.0 previa "ID acima do `ultimo` do
Registry" e "ID em número reservado". Ambas caíram por DA-098-001 e DA-098-002:
`TASK` é governado pelo Git e `ADR` pelo AMP-001, então o Registry não guarda o
contador desses dois e não pode julgá-los. Reintroduzi-las exigiria duplicar as
fontes de verdade que as decisões acabaram de unificar.

---

# 8. Decisões da Arquitetura (DA-098-001..007)

As quatro questões abertas na v1.0 foram decididas, e três determinações
adicionais ampliaram o escopo. Duas contrariam a recomendação da Engenharia —
registradas aqui com o motivo.

**DA-098-001 — o Git é a fonte da verdade para `TASK`.**
A próxima TASK é `max(TASK no histórico Git) + 1`. Nunca o maior número de um
documento, backlog ou memória. Cadeia: `Git → Registry → Documentos`, nunca o
inverso. *Contraria a recomendação da Engenharia*, que preferia contador manual
para não acoplar o validador ao histórico; a Arquitetura decidiu pela
imutabilidade do Git — documentos atrasam, commits não.

**DA-098-002 — `ADR` continua governada pelo AMP-001.**
O Registry **não** calcula o próximo ADR nem transcreve as reservas: apenas
declara `governadoPor: AMP-001`. *Contraria a recomendação da Engenharia*, que
propunha transcrever as 15 reservas; a Arquitetura decidiu evitar duas fontes de
verdade para a mesma informação.

**DA-098-003 — registrar TODOS os namespaces**, inclusive depreciados. Registry
é inventário, não catálogo.

**DA-098-004 — `DECISION` torna-se `LEGACY`.** Não será apagado nem renumerado;
documentos antigos permanecem válidos; nenhum `DECISION-XXX` novo pode ser
criado; referência futura aponta para `ADR`.

**DA-098-005 — o Registry não é manual: é metadado executável.** Cada namespace
declara nome, prefixo, fonte de governança, regra de numeração, status e
validador responsável — campos legíveis por ferramenta, não prosa.

**DA-098-006 — o Registry é documento normativo.** É a autoridade oficial sobre
criação de IDs, namespaces, gramática, estados e depreciação. Novo namespace
altera **primeiro** o Registry, depois os demais documentos.

**DA-098-007 — nova família de validação.** O `docs:validate` passa a ter cinco
famílias: `Structural`, `References`, `Contracts`, `Governance`, `Identifiers`.

---

# 9. Critérios de aceitação

| ID | Critério |
|---|---|
| **CB-001** | O Registry contém todos os 24 namespaces inventariados em §2 (DA-098-003) |
| **CB-002** | Namespace inexistente é recusado com ERRO (regra 5.2) |
| **CB-003** | Novo ID em namespace `LEGACY` (`DECISION-002`) é recusado com ERRO |
| **CB-004** | `TASK-092-A` **não** é reportado como colisão de `TASK-092` (AC-003) |
| **CB-005** | `DECISION-001` existente gera AVISO, não erro (DA-098-004) |
| **CB-006** | Cada namespace do Registry declara os seis campos de DA-098-005 |
| **CB-007** | O repositório atual passa com **0 erros** |
| **CB-008** | Cada regra 5.1–5.7 tem teste automatizado |

---

# 10. Entregáveis

1. Esta especificação (SPEC-002);
2. `docs/governance/registry/identifier-registry.json`;
3. Regras 5.1–5.7 em `scripts/contract-check.js` ou módulo irmão;
4. Testes em `scripts/tests/`, cobrindo CB-002 a CB-005.

---

# 11. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Especificação inicial do sistema de identificadores (TASK-098), baseada em inventário de 24 namespaces. |
| 1.1.0 | 07/08/2026 | Aprovada — DA-098-001..007 registradas; Registry como metadado executável e documento normativo; família Identifiers definida; regras dependentes de contador próprio de TASK/ADR removidas por unificação das fontes de verdade. |
