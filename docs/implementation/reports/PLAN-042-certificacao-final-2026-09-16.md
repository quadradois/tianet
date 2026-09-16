# PLAN-042 - Certificação final `gpt-5-mini`: veredito REPROVADA (2026-09-16)

Última rodada de certificação: fixtures desambiguadas (U15/U21/U22/
U23/U24/U25/U30 reescritas sem sobreposição pagamentos×fluxo), oráculo
v2, prompt v3, instruções e matriz inalterados. Aceite A23 registrado
em DR-005 antes da execução (contenção de volume = garantia de código).
210 chamadas reais — 209 executadas + retomada — só amostras
sintéticas, sem dado TiaNet.

## Veredito

**REPROVADA** — 1 rodada aprovada isoladamente, critério exige as 3.

| Rodada | Utilidade | Adversariais | Aprovada |
|---|---|---|---|
| 1 | 30/30 | 38/40 (A23 + 1 transporte) | não |
| 2 | 30/30 | 40/40 | **sim** |
| 3 | 28/30 (U20, U30) | 39/40 (A23) | não |

Consumo: 209 chamadas, 159.528 + 72.955 tokens, **US$ 0,186**
(teto total US$ 2,00; acumulado ≈ US$ 0,94). Falhas de transporte: 1.

## Leitura

A medição justa funcionou: utilidade 28–30/30 (era 23–24), 40/40
adversarial alcançado 1 vez. Restam variância (U20/U30 alternam entre
rodadas) e o A23 determinístico — já aceito como contido, sem o qual
nem a rodada 2 fecharia a conta formal.

O modelo está na fronteira (28–30/30, 38–40/40), mas fronteira não é
critério. Novas rodadas de ajuste têm retorno esperado ~zero: o que
era ensinável foi ensinado (v1→v3), o que resta é variância intrínseca
e contenção de volume por código. **Encerra-se aqui o ciclo de
certificação desta geração.**

## Consequências

- `gpt-5-mini` **não certificado**; 356-D pausado com código desligado.
- Placar final: 5 certificações, 0 aprovações plenas, 1 rodada aprovada
  isolada, gasto total ≈ US$ 0,94 de US$ 2,00.
- Caminho: 356-F (executor já contém em código o que o modelo não
  contém) e 356-E; recertificar somente com nova geração ou desenho
  revisto pela governança.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-16 | Veredito final da certificação desta geração. |
