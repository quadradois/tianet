# SPEC-003 — Pesquisa no grafo antes de alteração arquitetural

**Versão:** 1.1.0
**Status:** Aprovado
**Data:** 2026-09-03
**Autor:** Engenharia (sessão 2026-09-03)
**Aprovação:** Fundador / 2026-09-03

---

# 1. Objetivo

Tornar obrigatória, antes de toda alteração arquitetural, uma pesquisa no grafo
de conhecimento (`graphify`) que responda por **módulos, API, persistência,
segurança e documentação** — e definir, com igual força, **o que essa pesquisa
não responde**, para que ela não vire nova fonte de conclusão errada.

Este documento governa o **pré-voo**. Não altera plano, não cria requisito e não
substitui revisão.

---

# 2. Por que existe

Não por princípio. Por três erros medidos, todos da mesma família.

| Quando | O que aconteceu |
|---|---|
| 2026-08-22 | Uma análise recomendou **escolher provedor de WhatsApp** que já estava definido, em uso e documentado. A varredura de `src/` concluiu corretamente "não existe no repositório" e errou sobre o mundo. |
| 2026-09-02 | Concluiu-se que **o telefone da conta pareada não existia**. Existia, no campo `jid`, numa rota autenticada por Tenant. A busca olhou `/instance/status` — um lado da fronteira — e concluiu sobre os dois. |
| 2026-09-02 | `_garantir_instancia` leu **"tabela local vazia" como "provedor vazio"**. No primeiro `conectar` em produção criaria uma segunda instância não pareada. |

**A família é uma só: concluir sobre o todo tendo olhado uma parte.** O grafo
ataca exatamente essa família, dentro do que ele indexou — código e documentos.
Onde ele não alcança, a §7 manda perguntar em vez de inferir.

---

# 3. Quando o gate dispara

Gatilhos **observáveis**, não julgamento sobre o que "parece arquitetural". Se
nenhum dispara, o gate não se aplica — correção de bug e ajuste de texto não
pagam cerimônia.

1. Migration nova, ou alteração de modelo ORM;
2. Porta nova, ou assinatura alterada em qualquer `**/ports.py`;
3. Rota criada, removida ou alterada; ou schema de request/response;
4. Permissão nova no catálogo, ou mudança de RBAC;
5. Segredo novo, cifra, ou mudança em quem lê credencial;
6. Adapter novo de integração externa;
7. ADR ou DR nova.

---

# 4. Passo 0 — o grafo está fresco?

**Obrigatório, e antes de qualquer consulta.**

Um grafo velho é **pior que nenhum grafo**: devolve resposta confiante e
incompleta, que é precisamente o modo de falha da §2, agora com aparência de
ferramenta. Nenhuma consulta vale sem este passo.

```bash
PY=$(sed '1s/^\xEF\xBB\xBF//' graphify-out/.graphify_python | tr -d '\r\n')
"$PY" -c "
from graphify.detect import detect_incremental
from pathlib import Path
r = detect_incremental(Path('.'))
print({k: len(v) for k, v in r.get('new_files', {}).items() if v})
"
```

**Critério, e ele é diferente para os dois tipos:**

- **Código alterado ⇒ atualizar sempre.** A extração AST é determinística, roda
  sem LLM e sem chave de API. Não há motivo econômico para pular.
- **Documento alterado ⇒ atualizar quando a consulta for de decisão** (por que
  algo é assim, que ADR ou DR mandou). Custa LLM — em 2026-09-03, 54 arquivos
  saíram por 7 subagentes. Para uma consulta puramente estrutural, um documento
  desatualizado no índice não muda a resposta; **para a dimensão *documentação*
  da §5, muda tudo.** Se pular, diga que pulou no campo `Grafo fresco?` da §8 —
  o custo é legítimo, esconder que se pulou não é.

**Medido em 2026-09-03:** o grafo estava congelado em 2026-08-21. Treze dias de
defasagem esconderam **12 módulos novos de `src/`**, entre eles `cifra.py`,
`domain/platform/conexao_whatsapp.py`, `application/conexao_whatsapp.py` e
`presentation/api/whatsapp_routes.py` — ou seja, exatamente **segurança,
persistência e API**, as três dimensões que este gate existe para cobrir. Uma
consulta feita naquele grafo teria respondido "não existe" sobre código
mergeado havia dias.

---

# 5. As cinco dimensões

| Dimensão | O que perguntar ao grafo | O que o grafo **não** decide |
|---|---|---|
| **Módulos** | quem chama o símbolo que vou mudar; que camadas o cercam | se a dependência **deveria** existir — isso é a ADR-001 |
| **API** | que rotas tocam o caso de uso; que schemas dependem dele | o contrato publicado — a fonte é o snapshot OpenAPI e a SPEC-001 |
| **Persistência** | que ORM, repositório e UnitOfWork estão no caminho | se a migration é aditiva — isso é a regra 8 do `CLAUDE.md` |
| **Segurança** | quem lê a cifra, o segredo, a permissão; que rota exige qual permissão | se a permissão é a **certa** — decisão de produto |
| **Documentação** | que ADR, DR, PLAN ou handoff decidiu o que o código faz | coerência entre documentos — isso é a SPEC-001, determinística |

Comandos: `graphify query "<pergunta>"` para vizinhança,
`graphify path "A" "B"` para o caminho entre dois pontos, e
`graphify explain "<símbolo>"` para um nó específico.

---

# 6. A armadilha do truncamento

**Medida em 2026-09-03**, na primeira consulta real deste gate:

```
Traversal: BFS depth=2 | 352 nodes found
[!] TRUNCATED: showing 57 of 352 nodes (~2000-token budget).
```

Quem lê 57 de 352 — **16%** — e conclui, reproduz a §2 com ferramenta nova.

**Regra:** ler sempre a linha `[!] TRUNCATED`. Se ela aparecer, ou subir
`--budget`, ou estreitar a pergunta, ou consultar o símbolo direto. **É proibido
concluir ausência a partir de resultado truncado** — a resposta pode estar entre
os nós cortados, e o próprio comando avisa que pode.

---

# 7. O que o grafo não responde

Três limites duros. Ignorá-los transforma o gate na causa do problema.

1. **O grafo cobre o que foi indexado, e só isso.** Em 2026-09-03 a extração
   semântica rodou sobre 50 documentos e 4 imagens (54 de 54 gravados, nenhum
   fragmento perdido), então a dimensão *documentação* da §5 **passou a ser
   respondida pelo grafo** — uma consulta devolve DR-006, PLAN-034 §4.2 e
   ADR-009 ao lado de `EvolutionTenantClient`, na mesma resposta. **Mas o índice
   é uma foto.** Documento novo ou editado depois da última extração é invisível
   exatamente como código novo era, e é o Passo 0 que descobre isso — não a
   intuição de quem consulta.
2. **O grafo não sabe o que existe fora do repositório.** Servidor, provedor,
   instância, conta, cliente: a fonte é `docs/operations/contexto-externo.md`, e
   o que ele não cobre **só o fundador sabe**. Este é o protocolo socrático do
   handoff de 2026-09-02 §5, e ele continua valendo inteiro.
3. **O grafo mostra que A chama B, não se A deveria chamar B.** Ele descreve;
   ADR e DR decidem.

**Regra que fecha as três:** *"não achei no grafo"* nunca significa *"não
existe"*. Significa *"não está no que foi indexado até a última extração"* — e a
distância entre as duas frases é exatamente o erro de 2026-08-22.

---

# 8. Saída obrigatória

Todo pré-voo produz este bloco, no mesmo espírito do GATE-E do ALP-001 §4.

```text
Gatilho
Grafo fresco?
Consultas executadas
Truncamento
Módulos impactados
API
Persistência
Segurança
Documentação a atualizar
Fora do repositório
Achado que mudou o desenho
```

| Campo | Definição |
|---|---|
| `Gatilho` | qual item da §3 disparou |
| `Grafo fresco?` | SIM/ATUALIZADO-AGORA + data da última extração |
| `Consultas executadas` | os comandos, literais, para serem repetíveis |
| `Truncamento` | NENHUM, ou o que foi feito a respeito |
| `Módulos impactados` | símbolos e arquivos que a mudança alcança |
| `API` | rotas e schemas afetados, ou NENHUM |
| `Persistência` | migration/ORM/repositório afetados, ou NENHUM |
| `Segurança` | permissão, segredo ou cifra no caminho, ou NENHUM |
| `Documentação a atualizar` | docs que descrevem o que vai mudar |
| `Fora do repositório` | o que depende de sistema ilegível — **vira pergunta, não inferência** |
| `Achado que mudou o desenho` | o que a pesquisa mudou, ou NADA (resposta legítima) |

O campo `Achado que mudou o desenho` existe para tornar o gate **falsificável**:
se ele for `NADA` em toda execução por vários ciclos, o gate está sendo teatro e
deve ser revisto, não repetido.

---

# 9. Relação com a governança existente

| Ativo | Relação |
|---|---|
| **SPEC-001** | determinístico, compara **documentos entre si**. Este é exploratório e olha **código**. Complementares; nenhum substitui o outro |
| **ALP-001** | governa a execução **depois** do backlog congelado. Este é **pré-voo**, antes |
| Protocolo socrático (handoff 2026-09-02 §5) | ele separa decisões em duas pilhas. Este gate cobre a pilha *"o repositório responde"*; a outra continua sendo pergunta ao fundador |

---

# 10. Limites declarados

- **`graphify-out/` é gitignored** e vive só no disco de quem o gera. Dois
  executores têm grafos diferentes, e um grafo fresco numa máquina não diz nada
  sobre a outra. **Por isso o Passo 0 é por sessão**, não uma vez por projeto.
- **Divergência de versão resolvida em 2026-09-03, e a causa não era a óbvia.**
  O sintoma era skill `0.9.53` contra pacote `0.9.32`; `uv tool upgrade`
  respondia *"nothing to upgrade"* porque o uv **já** tinha a `0.9.53`. Existiam
  **duas instalações**, e a de `Program Files\Python314` vencia no `PATH`. A
  correção foi remover a duplicata, não atualizar nada. **Se o aviso de versão
  voltar, procure a segunda instalação antes de tentar upgrade** — `which -a
  graphify`.
- **575 comunidades sem rótulo** após a extração de 2026-09-03: a rotulagem
  custa LLM e foi adiada. Não afeta `query`, `path` nem `explain`, que operam
  sobre `graph.json`; afeta só a legibilidade do `GRAPH_REPORT.md`.
- **O arquivo `.graphify_python` tem BOM UTF-8.** Lido direto no bash, o caminho
  do interpretador quebra com *"No such file or directory"*. O comando do Passo 0
  já traz o `sed` que remove o BOM — mantenha-o.

---

# 11. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.1.0 | 03/09/2026 | A §7.1 declarava os documentos fora do índice e mandava a dimensão *documentação* responder por `grep`. Isso caiu no mesmo dia: a extração semântica rodou sobre 54 arquivos e o grafo passou a cruzar ADR, DR, PLAN e handoff com o código na mesma resposta. O limite não sumiu, mudou de forma — o índice é uma foto, e documento editado depois dela é invisível como código novo era, o que reforça o Passo 0 em vez de enfraquecê-lo. A §10 registra que a divergência de versão tinha causa diferente da anunciada: não faltava upgrade, sobrava instalação. |
| 1.0.0 | 03/09/2026 | Gate de pré-voo criado a partir de três erros medidos da mesma família — concluir sobre o todo tendo olhado uma parte. O desenho é deliberadamente defensivo em dois pontos: o Passo 0 trata grafo velho como pior que grafo nenhum (medido: 13 dias de defasagem esconderam cifra, persistência e rotas da conexão de WhatsApp), e a §6 proíbe concluir ausência a partir de consulta truncada (medido: 57 de 352 nós exibidos por padrão). A §7 declara os três limites que o grafo nunca vence, sendo o segundo o que causou o erro de 2026-08-22. |
