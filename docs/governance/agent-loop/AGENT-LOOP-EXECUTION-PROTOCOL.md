# TASK-087 — ALP-001 — Agent Loop Execution Protocol

**ID:** ALP-001

**Versão:** 1.0.0

**Status:** Vigente

**Data:** 2026-08-05

**Camada:** Governança de Processo

**Aplicação:** global — todos os EPICs, executados via Agent Loop.

---

# 1. Propósito

Definir **como a execução do trabalho é controlada** quando um Agent Loop implementa um
Execution Backlog congelado. O ALP-001 é o ativo de processo da equipe: global,
versionado, centralizado e reutilizável.

Separação de responsabilidades:

```
FOUNDATION
        │
        ▼
Define a arquitetura (o que é certo construir)

PLAN
        │
        ▼
Define o trabalho (o que construir)

ALP-001
        │
        ▼
Define como o trabalho será executado e controlado
```

O ALP-001 NÃO substitui o PLAN, NÃO altera o plano e NÃO cria novos requisitos.
Ele apenas governa a execução.

---

## 2. Estrutura do Agent Loop

```
SDD Congelado
        ↓
PLAN
        ↓
Execution Backlog (PLAN-N-EXEC)
        ↓
Agent Loop (execução sequencial das IMPs)
        ↓
Execution Gates (GATE-E1..En)
        ↓
Conclusão (backlog totalmente implementado)
```

Entrada mínima do Agent Loop:

- Execution Backlog com IMPs numeradas (ex.: IMP-042..IMP-064);
- arquitetura congelada (Foundation/Product/Domain/Architecture imutáveis);
- este protocolo (ALP-001).

---

## 3. Regra de agrupamento (5 IMPs por Gate)

Cada bloco de aproximadamente **5 IMPs** encerra com **um Execution Gate**.

Exemplo para um backlog de 23 IMPs (IMP-042..IMP-064):

```
IMP-042..046 → GATE-E1
IMP-047..051 → GATE-E2
IMP-052..056 → GATE-E3
IMP-057..061 → GATE-E4
IMP-062..064 → GATE-E5 (final de EPIC)
```

Exceções permitidas:

- blocos menores no final (ex.: 3 IMPs restantes → GATE final);
- blocos maiores somente mediante justificativa registrada no relatório do Gate
  anterior.

---

## 4. Conteúdo obrigatório de todo GATE-E

Todo relatório de Gate deve responder:

```text
IMPs executadas
Testes
Cobertura
Qualidade
Pendências
Riscos
Plano continua válido?
Pode seguir?
```

Campos mínimos e seus papel:

| Campo | Definição |
|-------|-----------|
| `IMPs executadas` | faixa das IMPs cobertas no bloco (ex.: `047..051`) |
| `Testes` | resultado da suíte (ex.: `214 passed`) |
| `Cobertura` | nível de cobertura da camada/pacote relevante (ex.: `98%`) |
| `Qualidade` | resultado de lint, mypy, black etc. |
| `Pendências` | dívidas ou itens abertos do bloco (se houver) |
| `Riscos` | riscos novos ou reavaliação dos previamente registrados |
| `Plano continua válido?` | SIM/COM AJUSTE/NÃO (justificar) |
| `Pode seguir?` | SIM/PARAR (justificativa) |

---

## 5. Condições de parada e escalonamento

### 5.1 Resolver autônomo (escopo do Execution Gate)

O Agent Loop decide sozinho e continua dentro do bloco:

- bug;
- refatoração local;
- teste de regressão;
- lint / mypy / black / cobertura;
- ajustes locais de implementação.

### 5.2 Escalar para arquitetura (somente quando houver)

- ADR (necessidade de nova ADR);
- Foundation (novos FOUNDATION-xxx);
- Capability; mudança em Capability Nap;
- Bounded Context; mudança de contexto;
- decisão irreversível;
- conflito documental oficial.

Em qualquer condição que-4, o Agent Loop **par** e escala ao Gestor/Arquiteto.
Durante a escalada, o Execution Gate reporta estado e bloqueia o fluxo.

---

## 6. Saída obrigatória de todo Gate

Todo GATE-E gera um relatório pequeno e autônomo, exemplo:

```text
GATE-E2

IMPs:
047..051

Resultado:
PASS

Testes:
214

Cobertura:
98%

Plano:
mantido

Arquitetura:
não impactada

Autorização:
seguir
```

O relatório é incluído como comentário do fim do bloco no Execution Backlog ou em
artefato de auditoria do EPIC; não gera documentos arquiteturais novos.

---

## 7. Referência nos Execution Backlogs

Os backlogs de execução devem fazer referência única ao protocolo no início:

> **A execução deste backlog deve seguir obrigatoriamente o AGENT-LOOP-EXECUTION-PROTOCOL (ALP-001).**

Nenhum backlog deve duplicar o conteúdo deste protocolo.

O **PLAN-003-EXEC** é o primeiro backlog a referenciar o ALP-001 (referência de
prefixo principal). Outros backlogs (EXEC de futuros EPICs) referenciam
imediatamente após a criação do PLAN.

---

## 8. Estado do processo

O ALP-001 é **ativo permanente** da camada de governança. Mudanças no processo
são centralizadas aqui e refletidas automaticamente em todos os backlogs futuros,
sem necessidade de edição individual.

**Não implementado ainda:** nenhum bloco IMP executado por este protocolo
(primeiro uso será o Agent Loop do PLAN-003-EXEC — IMP-042..064).

---

## Histórico de Versões

| Versão | Data | Autor | Resumo |
|--------|------|-------|--------|
| 1.0.0 | 2026-08-05 | Agente (governança de processo) | Criação do ALP-001 — Agent Loop Execution Protocol (TASK-087). |