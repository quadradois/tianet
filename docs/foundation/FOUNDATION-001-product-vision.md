# FOUNDATION-001 — Product Vision

**ID:** FOUNDATION-001

**Versão:** 2.0.0

**Status:** Aprovado

> **Auditoria aberta.** A correção do público-alvo em 2.0.0 invalida premissas de
> artefatos derivados da versão 1.0.0. EPICs, Features e o modelo de domínio
> podem carregar cerimônia institucional que não corresponde ao Credor
> individual. O levantamento do alcance ainda não foi feito.

---

# 1. Propósito

A TiaNet existe para simplificar a administração de operações de crédito.

Nossa missão é transformar controles manuais, planilhas e cálculos complexos em um processo seguro, previsível, auditável e simples de operar.

Mais do que registrar empréstimos, a TiaNet busca proporcionar tranquilidade ao Credor, garantindo que todas as operações financeiras sejam processadas com precisão e transparência.

---

# 2. Problema

Grande parte das operações de crédito de pequeno e médio porte ainda é administrada por meio de planilhas, cadernos ou sistemas genéricos.

Essa realidade gera:

- cálculos inconsistentes;
- erros de juros;
- dificuldade para calcular atrasos;
- ausência de histórico auditável;
- falta de previsibilidade;
- alto risco operacional.

A TiaNet nasce para eliminar esses problemas.

---

# 3. Público-Alvo

A TiaNet é para o **Credor individual**: a pessoa que empresta o próprio dinheiro e administra pessoalmente suas operações.

Perfil:

- empresta capital próprio, não de terceiros;
- opera sozinho, sem equipe;
- hoje controla por planilha, caderno ou aplicativo genérico;
- valoriza previsibilidade e prova do que foi combinado mais do que relatório analítico.

**Ele é uma pessoa só, e isso é determinante.** Não existe analista, mesa de crédito ou comitê. Quem cadastra o devedor é quem define o valor, aprova a operação e recebe o pagamento. Qualquer separação de funções entre humanos é ficção neste produto, e desenhar para ela produz cerimônia que ninguém executa.

A TiaNet **não** é para financeiras, correspondentes financeiros, empresas de crédito ou gestores de carteira de terceiros. Esses perfis exigem segregação de funções, alçadas e governança interna que este produto deliberadamente não modela.

## 3.1 O segundo operador é um agente de IA

O Credor não está sozinho na operação, mas seu par não é humano: um agente de IA atende os pedidos que chegam por canais de mensagem, registra o pré-cadastro e o submete ao Credor.

Essa é a única separação de funções real do produto: **o agente propõe, o Credor decide.** Ela justifica a existência de proposta com aprovação — que sem esse contexto pareceria burocracia herdada e seria removida por engano.

---

# 4. Proposta de Valor

A TiaNet oferece uma plataforma especializada para administração completa de operações de crédito.

Seu diferencial é possuir um Motor Financeiro capaz de processar toda a operação utilizando regras únicas, auditáveis e consistentes.

Toda informação financeira possui uma única fonte oficial de cálculo.

---

# 5. Princípios do Produto

## Princípio 01

Simplicidade antes da complexidade.

---

## Princípio 02

Uma única fonte oficial para todas as informações financeiras.

---

## Princípio 03

Todo cálculo deve ser reproduzível e auditável.

---

## Princípio 04

Automação deve reduzir trabalho, nunca reduzir transparência.

---

## Princípio 05

O domínio financeiro é o coração do produto e deve permanecer protegido de regras externas.

---

# 6. Objetivos Estratégicos

A evolução da TiaNet deverá buscar continuamente:

- reduzir erros operacionais;
- aumentar a produtividade do Credor;
- automatizar processos repetitivos;
- garantir rastreabilidade completa;
- oferecer previsibilidade financeira;
- permitir crescimento sustentável da plataforma.

---

# 7. Critérios de Sucesso

A Product Vision será considerada atendida quando a plataforma permitir que um Credor administre integralmente suas operações de crédito de forma simples, segura, previsível e auditável.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 2.0.0 | 16/08/2026 | Correção do público-alvo: o produto é para o Credor individual que empresta o próprio dinheiro, não para financeiras e correspondentes. A versão 1.0.0 descrevia organizações, contradizendo os §1, §2 e §7 do próprio documento, que sempre falaram de um Credor no singular controlando planilhas. Dessa contradição derivou a cerimônia institucional hoje presente no fluxo Comercial e de Contratos. Registrada também a separação real de funções: agente de IA propõe, Credor decide. Mudança maior por invalidar premissas de artefatos derivados. |
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Product Vision da TiaNet. |
