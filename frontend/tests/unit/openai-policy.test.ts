import { describe, expect, it } from "vitest";

import { validatedChallengeFromActionState, type OpenAIActionState } from "../../src/lib/openai/openai-policy";

function state(challenge: unknown): OpenAIActionState {
  return {
    kind: "problem",
    message: "falha",
    status: 502,
    correlationId: "corr",
    challenge,
  } as OpenAIActionState;
}

describe("política do desafio OpenAI", () => {
  it("preserva somente desafio vigente, fechado e no host oficial", () => {
    const valid = {
      verificationUrl: "https://auth.openai.com/codex/device",
      userCode: "ABCD-EFGH",
      expiresAt: "2099-01-01T00:00:00Z",
    };
    expect(validatedChallengeFromActionState(state(valid))).toEqual(valid);
    expect(validatedChallengeFromActionState(state({ ...valid, verificationUrl: "https://evil.example/device" }))).toBeUndefined();
    expect(validatedChallengeFromActionState(state({ ...valid, expiresAt: "2020-01-01T00:00:00Z" }))).toBeUndefined();
    expect(validatedChallengeFromActionState(state({ ...valid, accessToken: "não pode existir" }))).toBeUndefined();
  });
});
