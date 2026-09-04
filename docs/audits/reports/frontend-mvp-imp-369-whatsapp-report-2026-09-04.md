# Relatorio focal — IMP-369 Conexao do WhatsApp

**Plano relacionado:** PLAN-034 — Conexao do WhatsApp na plataforma
**Data:** 2026-09-04
**Status:** IMP-369 concluido, com quatro achados de review corrigidos. Rodada 2 pendente.

---

## 1. Resultado

O IMP-369 materializou a conexao do WhatsApp dentro da plataforma, em duas pecas:

- **Selo na barra lateral**, fora do menu, com dois estados — conectado e nao
  conectado. Le o **contexto operacional**, que ja e buscado em toda pagina, e
  nunca o provedor: o `GET` de estado vai ao Evolution a cada chamada, e um selo
  amarrado a ele custaria uma chamada externa por navegacao;
- **Tela em `/app/whatsapp`**, com botao explicito de conectar, QR, polling do
  pareamento e desconexao.

O QR **nao sai da consulta**. Ele e credencial de pareamento e vem apenas da acao
que chama o `POST`, protegido por `whatsapp.conexao.gerir` (decisao do IMP-368).

---

## 2. O que o review encontrou, e foi corrigido

Quatro achados, todos de logica nossa:

1. **Polling sem fim** — seguia o *estado* da conexao, entao ligava ao abrir a
   tela sem clicar e voltava a ligar depois de desconectar. Agora segue **o QR na
   tela**, com prazo de dois minutos;
2. **QR velho ressuscitando** — o resultado do conectar sobrevivia ao `refresh` e
   reaparecia apos o logout. Corrigido pela estrutura: **uma acao so** para as
   duas operacoes, entao desconectar substitui o resultado;
3. **Mensagem prometendo QR inexistente** quando o provedor ainda estava gerando;
4. **Selo contraditorio** quando `pareada: true` vinha com `numero: null`.

---

## 3. Escopo preservado

- Nenhuma operacao nova na API: a tela consome as quatro rotas que o IMP-368 ja
  publicou;
- `Idempotency-Key` permanece ausente nas escritas, conforme a
  [ADR-019](../../architecture/adrs/ADR-019-isencao-de-idempotency-key-nas-escritas-da-conexao-de-whatsapp.md);
- Um unico Client Component novo, apos o guardrail do IMP-286 reprovar dois — o
  polling foi absorvido como hook da propria tela.

---

## 4. Evidencia visual

| `frontend-mvp-imp-369-whatsapp-ausente-desktop.png` | 1440x900 | `002e65e4b7bfb13137b2c97fc2837402c5c205162051035378573ea818702276` |
| `frontend-mvp-imp-369-whatsapp-ausente-mobile.png` | 390x844 | `1aee852cd195bfd956875d904380176cdcb16bfa4456242b7c44812947f6ac23` |
| `frontend-mvp-imp-369-whatsapp-pareada-desktop.png` | 1440x900 | `8839a06cc46d6189800aacb8e87c2139f9a462ca69da899ed057a53b77998a5b` |
| `frontend-mvp-imp-369-whatsapp-pareada-mobile.png` | 390x844 | `32938a24c4d15f6c4eb75f15bf081b80ca23454ee68e6cd0f03b4004c9192912` |
| `frontend-mvp-imp-369-whatsapp-qr-desktop.png` | 1440x900 | `7e7021c7cb721b3d05adb6657ed38e8ade5eca7a659fcd17ad80e873c61419a0` |
| `frontend-mvp-imp-369-whatsapp-qr-mobile.png` | 390x844 | `73713e24ffc5375fab1614e5851acf99f1f67a651b3b8fc9513802b5b17ad717` |

---

## 5. Gates observados

- Jornada Playwright: **18 testes**, desktop e mobile, cobrindo ausente, QR,
  pareada, somente-leitura, o ciclo completo ate desconectar, e a **ausencia de
  polling** numa instancia pendente;
- a11y por axe **sem violacao critica ou seria**, inclusive com o QR na tela;
- Backend: 1231 testes, ruff, black, mypy sobre 268 arquivos;
- Contratos: 173/173 no gate documental, 42 de contrato e 135 de BFF no frontend.

---

## 6. Historico de Versoes

| Versao | Data | Descricao |
|---------|------|-----------|
| 1.1.0 | 04/09/2026 | Novo SHA da evidencia `qr-desktop`: o IMP-371 trocou o texto sob o codigo — de "expira em segundos, gere outro" para o par que conta a verdade nos dois estados do laco de renovacao. As outras cinco evidencias seguem identicas, e a `qr-mobile` nao mudou porque o texto fica fora do recorte de 390x844. **Quem pegou a divergencia foi o gate**, nao o review: `test:certification` exige que o SHA vigente de cada PNG apareca num relatorio, e ele reprovou. |
| 1.0.0 | 04/09/2026 | Relatorio focal do IMP-369, com as seis evidencias visuais fixadas por SHA. Registra os quatro achados do review e o que cada correcao mudou — dois deles tinham a mesma raiz: tratar o resultado da acao como se fosse o estado do servidor. |
