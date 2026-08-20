import { randomBytes } from "node:crypto";

import { describe, expect, it, vi } from "vitest";

import { RefreshCoordinator, type BffDependencies, type FetchLike } from "@/lib/bff/backend.server";
import {
  agendaCommand,
  changeCommitment,
  changeReminder,
  createCommitment,
  createReminder,
  listAgenda,
  listCommunications,
  registerCommunication,
} from "@/lib/bff/agenda-comunicacao.server";
import type { OperationalContext } from "@/lib/bff/context.server";
import { sealSession, sessionCookieName, type BffConfig, type SessionData } from "@/lib/bff/session.server";

const NOW = new Date("2026-08-14T12:00:00.000Z");
const TENANT_ID = "00000000-0000-4000-8000-000000000001";
const USER_ID = "00000000-0000-4000-8000-000000000002";
const WALLET_ID = "00000000-0000-4000-8000-000000000003";
const PROFILE_ID = "00000000-0000-4000-8000-000000000004";
const DEBTOR_ID = "00000000-0000-4000-8000-000000000010";
const LOAN_ID = "00000000-0000-4000-8000-000000000040";
const COMMITMENT_ID = "00000000-0000-4000-8000-000000000080";
const REMINDER_ID = "00000000-0000-4000-8000-000000000081";
const COMMUNICATION_ID = "00000000-0000-4000-8000-000000000082";
const NOTIFICATION_ID = "00000000-0000-4000-8000-000000000083";
const JOB_ID = "00000000-0000-4000-8000-000000000084";
const OTHER_WALLET = "00000000-0000-4000-8000-000000000099";

function config(): BffConfig {
  return { backendUrl: "http://backend.agenda.invalid", origin: "http://frontend.agenda.invalid", production: false, loginTenantIdentifier: "ACME", currentKeyId: "current", currentKey: randomBytes(32) };
}

const session: SessionData = { accessToken: "access-sensitive", accessTokenExpiresAt: "2026-08-14T12:15:00Z", refreshToken: "refresh-sensitive", refreshTokenExpiresAt: "2026-08-21T12:00:00Z", tenantId: TENANT_ID, userId: USER_ID };

function context(permissions: readonly string[]): OperationalContext {
  return { carteira_padrao: { id: WALLET_ID, nome: "Carteira" }, perfil: permissions.length ? { id: PROFILE_ID, nome: "Operador" } : null, permissoes: permissions, tenant: { id: TENANT_ID, identificador_institucional: "ACME", nome: "ACME" }, usuario: { email: "user@example.test", id: USER_ID, nome: "Operador" } };
}

async function cookieStore(selected: BffConfig) {
  const values = new Map<string, string>();
  values.set(sessionCookieName(selected), await sealSession(session, selected, NOW));
  return {
    get(name: string) { const value = values.get(name); return value ? { value } : undefined; },
    set(name: string, value: string) { values.set(name, value); },
  };
}

function dependencies(selected: BffConfig, fetch: FetchLike, timeoutMs = 1_000): BffDependencies {
  return { config: selected, fetch, now: () => NOW, timeoutMs, refreshCoordinator: new RefreshCoordinator() };
}

function commitment(carteira_id = WALLET_ID) {
  return { agenda_item_id: COMMITMENT_ID, atualizado_em: null, carteira_id, devedor_id: DEBTOR_ID, emprestimo_id: LOAN_ID, estado: "aberto", previsto_para: "2026-08-14T15:00:00Z", tenant_id: TENANT_ID, titulo: "Retorno combinado", usuario_solicitante_id: USER_ID };
}

function reminder(carteira_id = WALLET_ID) {
  return { agenda_item_id: COMMITMENT_ID, carteira_id, enviado_por_usuario_id: USER_ID, estado: "programa", horario: "2026-08-14T14:30:00Z", lembrete_id: REMINDER_ID, mensagem: "Ligar antes do retorno", tenant_id: TENANT_ID };
}

function communication(carteira_id = WALLET_ID) {
  return { agenda_item_id: COMMITMENT_ID, canal: "telefone", carteira_id, cobranca_acao_id: null, devedor_id: DEBTOR_ID, emprestimo_id: LOAN_ID, ocorrido_em: "2026-08-14T16:00:00Z", registro_id: COMMUNICATION_ID, responsavel_id: USER_ID, resultado: "Retorno agendado", resumo: "Contato realizado", tenant_id: TENANT_ID };
}

function notification() {
  return { carteira_id: WALLET_ID, codigo_resultado: null, estado: "enviado", id: NOTIFICATION_ID, job_id: JOB_ID, lembrete_id: REMINDER_ID, provider_message_id: "provider-ok", resultado_em: null };
}

describe("BFF Agenda/Comunicacao", () => {
  it("consulta Agenda e Comunicacao sem Idempotency-Key e somente com Carteira propria", async () => {
    const selected = config();
    const seen: Array<[string, boolean, string | null]> = [];
    const backend = vi.fn<FetchLike>(async (request) => {
      const url = new URL(request.url);
      seen.push([url.pathname, request.headers.has("Idempotency-Key"), url.searchParams.get("carteira_id")]);
      if (url.pathname === "/credit/agenda") return Response.json({ compromissos: [commitment()], lembretes: [reminder()], total: 2 }, { headers: { "X-Correlation-ID": "corr-agenda" } });
      return Response.json({ registros: [communication()], total: 1 }, { headers: { "X-Correlation-ID": "corr-com" } });
    });
    await expect(listAgenda(await cookieStore(selected), context(["agenda.ler"]), { devedorId: DEBTOR_ID, incluirLembretes: true }, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    await expect(listCommunications(await cookieStore(selected), context(["comunicacao.ler"]), { devedorId: DEBTOR_ID }, dependencies(selected, backend))).resolves.toMatchObject({ kind: "ready" });
    expect(seen).toEqual([
      ["/credit/agenda", false, WALLET_ID],
      ["/credit/comunicacoes", false, WALLET_ID],
    ]);
  });

  it("nao chama backend sem permissao exata", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    await expect(listAgenda(await cookieStore(selected), context(["agenda.*"]), { incluirLembretes: true }, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    await expect(listCommunications(await cookieStore(selected), context(["comunicacao.*"]), {}, dependencies(selected, backend))).resolves.toEqual({ kind: "denied" });
    expect(backend).not.toHaveBeenCalled();
  });

  it("envia Idempotency-Key nas mutacoes de compromisso e comunicacao", async () => {
    const selected = config();
    const seen: Array<[string, boolean]> = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      seen.push([url.pathname, request.headers.has("Idempotency-Key")]);
      if (url.pathname.includes("/comunicacoes")) return Response.json(communication());
      return Response.json(commitment());
    };
    const commitmentForm = new FormData();
    commitmentForm.set("idempotency_key", "idem-agenda");
    commitmentForm.set("devedor_id", DEBTOR_ID);
    commitmentForm.set("titulo", "Retorno combinado");
    commitmentForm.set("previsto_para", "2026-08-14T15:00:00Z");
    await expect(createCommitment(await cookieStore(selected), context(["agenda.compromisso.gerir"]), commitmentForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    const communicationForm = new FormData();
    communicationForm.set("idempotency_key", "idem-com");
    communicationForm.set("devedor_id", DEBTOR_ID);
    communicationForm.set("canal", "telefone");
    communicationForm.set("ocorrido_em", "2026-08-14T16:00:00Z");
    communicationForm.set("resumo", "Contato");
    communicationForm.set("resultado", "Retorno agendado");
    await expect(registerCommunication(await cookieStore(selected), context(["comunicacao.registrar"]), communicationForm, dependencies(selected, backend))).resolves.toMatchObject({ kind: "success" });
    expect(seen).toEqual([
      [`/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/agenda/compromissos`, true],
      [`/credit/carteiras/${WALLET_ID}/devedores/${DEBTOR_ID}/comunicacoes`, true],
    ]);
  });

  it("envia Idempotency-Key nas demais mutacoes contratadas", async () => {
    const selected = config();
    const seen: string[] = [];
    const backend: FetchLike = async (request) => {
      const url = new URL(request.url);
      expect(request.headers.get("Idempotency-Key")).toBeTruthy();
      seen.push(url.pathname);
      if (url.pathname.includes("/lembretes/") && url.pathname.endsWith("/enviar")) return Response.json(notification());
      if (url.pathname.endsWith("/lembretes")) return Response.json(reminder());
      if (url.pathname.includes("/lembretes/")) return Response.json(reminder());
      return Response.json(commitment());
    };
    const deps = dependencies(selected, backend);
    const permissions = context(["agenda.compromisso.gerir", "agenda.lembrete.gerir", "notificacao.conciliar"]);
    const baseReminder = new FormData();
    baseReminder.set("idempotency_key", "idem-reminder");
    baseReminder.set("agenda_item_id", COMMITMENT_ID);
    baseReminder.set("horario", "2026-08-14T14:30:00Z");
    baseReminder.set("mensagem", "Ligar antes");
    await expect(createReminder(await cookieStore(selected), permissions, baseReminder, deps)).resolves.toMatchObject({ kind: "success" });
    for (const command of ["reagendar-compromisso", "concluir-compromisso", "cancelar-compromisso"]) {
      const form = new FormData();
      form.set("idempotency_key", `idem-${command}`);
      form.set("agenda_item_id", COMMITMENT_ID);
      form.set("command", command);
      if (command === "reagendar-compromisso") form.set("novo_horario", "2026-08-15T15:00:00Z");
      await expect(changeCommitment(await cookieStore(selected), permissions, form, deps)).resolves.toMatchObject({ kind: "success" });
    }
    for (const command of ["reagendar-lembrete", "enviar-lembrete", "concluir-lembrete", "cancelar-lembrete"]) {
      const form = new FormData();
      form.set("idempotency_key", `idem-${command}`);
      form.set("lembrete_id", REMINDER_ID);
      form.set("command", command);
      if (command === "reagendar-lembrete") form.set("novo_horario", "2026-08-15T14:30:00Z");
      if (command === "enviar-lembrete") {
        form.set("motivo", "Conciliacao manual");
        form.set("notification_id", NOTIFICATION_ID);
        form.set("provider_message_id", "provider-ok");
      }
      await expect(changeReminder(await cookieStore(selected), permissions, form, deps)).resolves.toMatchObject({ kind: "success" });
    }
    expect(seen).toEqual([
      `/credit/agenda/compromissos/${COMMITMENT_ID}/lembretes`,
      `/credit/agenda/compromissos/${COMMITMENT_ID}/reagendar`,
      `/credit/agenda/compromissos/${COMMITMENT_ID}/concluir`,
      `/credit/agenda/compromissos/${COMMITMENT_ID}/cancelar`,
      `/credit/agenda/lembretes/${REMINDER_ID}/reagendar`,
      `/credit/agenda/lembretes/${REMINDER_ID}/enviar`,
      `/credit/agenda/lembretes/${REMINDER_ID}/concluir`,
      `/credit/agenda/lembretes/${REMINDER_ID}/cancelar`,
    ]);
  });

  it("rejeita 200 incompleto ou de outra Carteira sem fabricar vazio", async () => {
    const selected = config();
    const missing = await listAgenda(await cookieStore(selected), context(["agenda.ler"]), { incluirLembretes: true }, dependencies(selected, async () => Response.json({ compromissos: [{ ...commitment(), atualizado_em: undefined }], lembretes: [], total: 1 })));
    expect(missing).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
    const cross = await listCommunications(await cookieStore(selected), context(["comunicacao.ler"]), {}, dependencies(selected, async () => Response.json({ registros: [communication(OTHER_WALLET)], total: 1 })));
    expect(cross).toMatchObject({ kind: "problem", problem: { status: 502, codigo: "resposta_backend_invalida" } });
  });

  it("mapeia 400, 401, 403, 404, 409, 422 e 5xx com correlation e mensagem publica segura", async () => {
    for (const [status, expected] of [[400, "payload_invalido"], [401, "autenticacao_recusada"], [403, "acesso_negado"], [404, "recurso_indisponivel"], [409, "conflito_estado"], [422, "regra_violada"], [500, "erro_tecnico"]] as const) {
      const selected = config();
      const result = await listAgenda(await cookieStore(selected), context(["agenda.ler"]), { incluirLembretes: true }, dependencies(selected, async () => Response.json({ codigo: expected, mensagem: "stack cross-carteira" }, { status, headers: { "X-Correlation-ID": "corr-safe" } })));
      expect(result.kind).toBe("problem");
      if (result.kind === "problem") {
        if (status === 401) expect(result.problem.correlationId).toMatch(/^[A-Za-z0-9._:-]{1,128}$/);
        else expect(result.problem.correlationId).toBe("corr-safe");
        expect(result.problem.codigo).toBe(status === 401 ? "sessao_invalida" : expected);
        expect(result.problem.mensagem).not.toContain("cross-carteira");
      }
    }
  });

  it("correlaciona 400 local sem chamar backend", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const result = await agendaCommand(await cookieStore(selected), context(["agenda.compromisso.gerir"]), new FormData(), dependencies(selected, backend));
    expect(result).toMatchObject({ kind: "problem", status: 400 });
    expect(result.correlationId).toMatch(/^[A-Za-z0-9._:-]{1,128}$/);
    expect(backend).not.toHaveBeenCalled();
  });

  it("normaliza Idempotency-Key invalida sem estourar a action", async () => {
    const selected = config();
    const backend = vi.fn<FetchLike>();
    const form = new FormData();
    form.set("idempotency_key", "chave invalida com espacos");
    form.set("devedor_id", DEBTOR_ID);
    form.set("titulo", "Retorno combinado");
    form.set("previsto_para", "2026-08-14T15:00:00Z");
    const result = await createCommitment(await cookieStore(selected), context(["agenda.compromisso.gerir"]), form, dependencies(selected, backend));
    expect(result).toMatchObject({ kind: "problem", status: 400 });
    expect(result.correlationId).toMatch(/^[A-Za-z0-9._:-]{1,128}$/);
    expect(backend).not.toHaveBeenCalled();
  });
});
