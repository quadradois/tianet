# US-114 - Cancelar Trabalho de Lembrete Inelegivel

**ID:** US-114

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** cancelar o trabalho automatico quando o Lembrete deixar de ser elegivel,
**para** impedir contato obsoleto.

---

# 2. Critérios de Aceitação

- concluir ou cancelar Lembrete cancela o job pendente na mesma transacao;
- job em processamento recebe pedido de cancelamento cooperativo;
- handler revalida a origem antes do efeito externo;
- job obsoleto termina sem enviar e registra motivo protegido;
- notificacao ja aceita nao e declarada como desfeita.

---

# 3. Regras de Negócio Relacionadas

- Lembrete terminal nao reabre;
- cancelamento nao apaga historico nem fato externo confirmado.

---

# 4. Dependências

- FEATURE-042 - Automatizar Lembretes Operacionais;
- US-113 - Agendar Lembrete Automatico;
- US-081 - Manter Item de Agenda.

---

# 5. Observações Técnicas

Cancelamento e cooperativo conforme DA-1013 do Discovery EPIC-010.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Cancelar Trabalho de Lembrete Inelegivel. |
