# EPIC-004 - Discovery/SDD de Contratos de Credito

**ID:** EPIC-004-DISCOVERY

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Discovery materializa o inicio do EPIC-004 - Contratos de Credito.

O objetivo e definir escopo, fronteiras, fluxos, riscos, contratos de integracao
e plano inicial de testes antes de qualquer implementacao. O EPIC-004 deve
consumir a proposta aprovada entregue pelo Comercial e gerar um contrato formal
rastreavel, sem executar Motor Financeiro.

---

# 2. Contexto

O EPIC-003 encerrou o ciclo Comercial com uma saida logica de proposta aprovada
para Contratos. O roadmap oficial define a sequencia:

1. EPIC-003 - Comercial;
2. EPIC-004 - Contratos de Credito;
3. EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

Contratos e o contexto que transforma uma decisao comercial aprovada em acordo
formal. Ele nao processa saldo, parcelas, juros, quitacao ou memoria de calculo.

---

# 3. Fronteiras

## Dentro do EPIC-004

- criar Contrato de Credito a partir de proposta aprovada;
- validar proposta aprovada, Tenant, Carteira e Devedor;
- preservar parametros aprovados como snapshot contratual;
- consultar contrato por ID;
- listar contratos por Carteira, Devedor, estado e periodo;
- registrar assinatura ou formalizacao;
- liberar contrato formalizado como entrada logica para Motor Financeiro futuro;
- cancelar contrato ainda nao liberado;
- encerrar contrato sem alterar operacao financeira;
- auditar escritas e transicoes contratuais;
- proteger API por IAM/RBAC e isolamento por Tenant/Carteira.

## Fora do EPIC-004

- calcular juros, amortizacao, saldo, quitacao ou memoria de calculo;
- criar Emprestimo, Parcela ou Pagamento;
- executar Motor Financeiro;
- integrar assinatura digital externa;
- liberar dinheiro, PIX, banco ou boleto;
- cobrar inadimplencia, criar agenda ou comunicacao automatica;
- renegociar contrato ja executado.

---

# 4. Contratos de Integracao

## Entrada vinda do Comercial

O EPIC-004 consome apenas proposta aprovada. A entrada logica minima e:

- `tenant_id`;
- `carteira_id`;
- `devedor_id`;
- `proposta_comercial_id`;
- parametros comerciais aprovados;
- usuario aprovador;
- instante de aprovacao.

Proposta inexistente, nao aprovada, de outro Tenant/Carteira ou com Devedor
inativo deve ser recusada sem revelar dados cross-tenant.

## Saida para Motor Financeiro futuro

O EPIC-004 entrega apenas um contrato formalizado/liberavel:

- `contrato_id`;
- `tenant_id`;
- `carteira_id`;
- `devedor_id`;
- snapshot dos parametros contratuais;
- estado contratual;
- usuario e instante da formalizacao;
- referencia para proposta aprovada.

O Motor Financeiro futuro decidira como transformar essa entrada em Emprestimo,
Parcelas, Pagamentos e Memoria de Calculo.

---

# 5. Estados Candidatos

- `rascunho`;
- `formalizado`;
- `assinado`;
- `liberado_para_motor`;
- `cancelado`;
- `encerrado`.

Estados terminais nao podem voltar a fluxo operacional. Contrato liberado para
Motor nao pode ter parametros contratuais alterados.

---

# 6. Riscos

| Risco | Mitigacao |
|---|---|
| Contratos absorver Motor Financeiro | Guardrail anti-Motor no EPIC-004. |
| Criar contrato sem proposta aprovada | Validacao obrigatoria do contrato logico vindo do Comercial. |
| Snapshot contratual editavel | Invariante de imutabilidade apos formalizacao/liberacao. |
| Vazamento cross-tenant | 404 indistinguivel para recursos fora do Tenant/Carteira. |
| Assinatura externa virar dependencia prematura | Registro interno de assinatura no MVP; integracao externa fora de escopo. |
| Liberacao ser confundida com desembolso financeiro | EPIC-004 libera entrada logica para Motor; nao libera dinheiro. |

---

# 7. Plano Inicial de Testes

- suites de dominio para ContratoCredito, estados e eventos;
- guardrail anti-Motor para impedir Emprestimo, Parcela, Pagamento e calculos;
- migration aditiva de contratos e eventos/decisoes contratuais;
- repositories com filtros por Tenant, Carteira, Devedor e estado;
- application services com validacao de proposta aprovada;
- API protegida por IAM/RBAC;
- OpenAPI com 401/403/404/409/422;
- recertificacao global com `pytest`, `ruff`, `black`, `mypy`, `docs:validate`
  e `docs:test`.

---

# 8. Resultado do Discovery

O EPIC-004 pode seguir para plano tecnico de implementacao, desde que o plano
mantenha Contratos como contexto de formalizacao e preserve Motor Financeiro
como unica autoridade de calculo.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Discovery/SDD inicial do EPIC-004 - Contratos de Credito. |
