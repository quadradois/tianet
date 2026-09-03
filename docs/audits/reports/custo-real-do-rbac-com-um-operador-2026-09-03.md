# Custo real do RBAC num sistema de um operador

**Data:** 2026-09-03
**Autor:** Engenharia
**Motivo:** pergunta do fundador em 2026-09-03 — *"com um usuário só, para que serve controle de permissão?"*

---

# 1. A pergunta

A TiaNet é operada por **um humano**, com todas as permissões
([ADR-003](../../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md) §60).
O sistema tem **56 permissões**, perfis, atribuição de perfil a usuário, e
verificação a cada requisição.

Um usuário que dá permissão a si mesmo, ou que se limita de fazer algo, é
absurdo. A pergunta é legítima: **isso está protegendo alguma coisa?**

---

# 2. O que existe, medido

Separando o que é **autenticação** (provar quem você é — necessária mesmo com um
usuário) do que é **autorização** (decidir o que você pode — só faz sentido com
mais de um ator).

## 2.1 Autorização — o que está em questão

| Onde | Linhas |
|---|---|
| `application/perfis_acesso.py` | 521 |
| `application/autorizacao.py` | 254 |
| `application/iam_catalogo.py` | 89 |
| `domain/platform/perfil.py` | 112 |
| `domain/platform/permissao.py` | 36 |
| **Subtotal `src/`** | **1.012** |
| Testes dedicados | 857 |
| Frontend (tela, BFF, policy) | 787 |
| **Total** | **2.656 linhas** |

Mais: **4 tabelas** no banco (`permissao`, `perfil_acesso`, `perfil_permissao`,
`usuario_perfil`), **10 operações** da API para gerir perfis e permissões, e
**~96 declarações** de `exigir_permissao` espalhadas pelas rotas.

## 2.2 Autenticação — fora de questão

734 linhas (`autenticacao.py`, `credenciais.py`, `sessao.py`) e 8 operações
(`/auth/login`, `/auth/logout`, `/auth/refresh`, troca de credencial). **Isso
seria necessário com um usuário ou com mil**, e não entra nesta conta.

## 2.3 Custo que continua correndo

- **Uma consulta ao banco por requisição protegida.** `exigir_permissao` abre um
  UnitOfWork e chama `find_by_usuario_id` a cada chamada. Com um operador e sem
  carga, é irrelevante hoje.
- **Cada endpoint novo custa uma permissão.** Adicionar rota implica acrescentar
  entrada no catálogo, subir `CATALOGO_PERMISSOES_VERSAO`, e cobrir 401/403 em
  teste. O IMP-367 pagou isso por duas permissões.

---

# 3. O que isso protege hoje

**Nada.** Há um humano, ele tem tudo, e não existe segundo ator provisionado.

Este relatório nasce de um erro concreto: em 2026-09-03 um review classificou
como *escalada de privilégio* o fato de o QR de pareamento sair sob permissão de
leitura, e a engenharia escreveu isso em seis documentos antes de o fundador
apontar que **o usuário somente-leitura não existe**. A separação
`whatsapp.conexao.ler` / `.gerir` não protegia ninguém.

---

# 4. O que isso vai proteger, e aí muda tudo

**O robô.** O PLAN-033 constrói o copiloto como **segundo Principal** — usuário e
perfil próprios, provisionados pelo IMP-355 — e a garantia de que ele não faz
besteira é **técnica, não de prompt**:

> *"O copilot não pode aprovar proposta. A garantia é técnica: o IMP-360 cria
> `comercial.proposta.submeter`, mantém `comercial.proposta.decidir` separado e
> **prova que o perfil `copilot` não recebe `decidir`**."*
> — PLAN-033, Regra Inviolável nº 2

O mesmo vale para as demais regras invioláveis: o copiloto lê carteira só no
contexto Operadora, não faz escrita financeira, e não decide nada. **Tudo isso é
imposto por permissão.**

Sem RBAC, a única barreira entre o robô e a aprovação de um empréstimo seria a
instrução em linguagem natural — que é exatamente o tipo de barreira que não se
sustenta.

---

# 5. Conclusão

**O RBAC não é peso à toa. É pago adiantado.**

Ele não protege ninguém hoje porque o ator que ele existe para conter — o
copiloto — ainda não foi provisionado. No dia em que for, ele deixa de ser
preparação e passa a ser a **única** coisa que impede um agente de LLM de decidir
crédito.

**O que muda a partir deste relatório é a linguagem, não o código:**

- **Parar de chamar de proteção o que hoje é preparação.** Foi essa confusão que
  produziu a ficção do "usuário somente-leitura" e seis documentos errados. Uma
  permissão que não tem de quem proteger deve ser descrita como *reservada para o
  copiloto*, não como controle de acesso vigente.
- **Uma permissão nova precisa dizer de quem ela protege.** Se a resposta for
  "de ninguém, por enquanto", tudo bem — mas escrito, e não subentendido.

**Não recomendo remover.** Custaria mexer em ~96 declarações de rota, 4 tabelas e
uma tela, para reconstruir tudo na Fase C — e o intervalo entre remover e
reconstruir é justamente quando o robô entra.

**Não recomendo otimizar agora.** A consulta por requisição some com cache ou com
as permissões dentro do JWT, mas otimizar acesso a banco num sistema de um
usuário sem carga é resolver problema que não existe.

---

# 6. O que fica para o fundador decidir

1. **Confirmar que o copiloto continua no plano.** Toda esta conta se apoia
   nisso. Se o copiloto sair do roadmap, o RBAC vira, aí sim, peso a remover — e
   este relatório deve ser reaberto.
2. **Se novas permissões devem continuar sendo criadas** enquanto o segundo ator
   não existe, ou se paramos de criá-las até o IMP-355 provisionar o copiloto.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 03/09/2026 | Levantamento pedido pelo fundador após a engenharia descrever como "escalada de privilégio" um cenário sem ator. Medido: 2.656 linhas, 4 tabelas, 10 operações e uma consulta por requisição servem hoje a zero atores. A conclusão inverte a pergunta — não é peso à toa, é pago adiantado, porque a garantia de que o copiloto não aprova empréstimo é RBAC e não prompt (PLAN-033, regra inviolável 2). O que muda é a linguagem: preparação deixa de ser chamada de proteção. |
