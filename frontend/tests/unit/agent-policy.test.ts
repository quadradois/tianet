import { describe, expect, it } from "vitest";

import { hasExactPermission, isAgentInbox, isAgentInboxEntry } from "../../src/lib/agent/agent-policy";

const ENTRADA = {
  provider_input_id: "a",
  remetente_normalizado: "556299999999",
  classe: "operadora",
  texto: "ola",
  estado: "recebida",
  recebido_em: "2026-09-19T12:00:00.000Z",
};

describe("agent-policy", () => {
  it("exige permissão exata, sem prefixo", () => {
    expect(hasExactPermission(["agent.inbox.ler"], "agent.inbox.ler")).toBe(true);
    expect(hasExactPermission(["agent.inbox.*"], "agent.inbox.ler")).toBe(false);
    expect(hasExactPermission([], "agent.inbox.ler")).toBe(false);
  });

  it("aceita inbox bem formada e recusa tipos errados", () => {
    expect(isAgentInboxEntry(ENTRADA)).toBe(true);
    expect(isAgentInboxEntry({ ...ENTRADA, texto: null })).toBe(true);
    expect(isAgentInboxEntry({ ...ENTRADA, total: 1 })).toBe(true);
    expect(isAgentInboxEntry({ ...ENTRADA, provider_input_id: 1 })).toBe(false);
    expect(isAgentInboxEntry(null)).toBe(false);
    expect(isAgentInbox({ total: 1, operadora: 1, pre_cadastro: 0, recentes: [ENTRADA] })).toBe(true);
    expect(isAgentInbox({ total: "1", operadora: 1, pre_cadastro: 0, recentes: [] })).toBe(false);
    expect(isAgentInbox({ total: 1, operadora: 1, pre_cadastro: 0, recentes: [null] })).toBe(false);
  });
});
