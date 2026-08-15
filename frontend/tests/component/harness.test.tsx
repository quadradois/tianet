import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import Home from "../../src/app/page";
import { server } from "../mocks/server";

function HarnessToggle() {
  const [enabled, setEnabled] = useState(false);
  return (
    <button type="button" onClick={() => setEnabled((current) => !current)}>
      {enabled ? "Harness ativo" : "Ativar harness"}
    </button>
  );
}

describe("component harness", () => {
  it("renderiza o placeholder existente por papel e nome", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: "Frontend MVP" })).toBeInTheDocument();
  });

  it("renderiza por papel e nome e executa uma interacao de usuario", async () => {
    const user = userEvent.setup();
    render(<HarnessToggle />);

    await user.click(screen.getByRole("button", { name: "Ativar harness" }));

    expect(screen.getByRole("button", { name: "Harness ativo" })).toBeInTheDocument();
  });

  it("intercepta um recurso interno do harness sem simular contrato de produto", async () => {
    const lifecycle = { active: true } as const;
    server.use(
      http.get("http://msw.harness.invalid/lifecycle", () => HttpResponse.json(lifecycle)),
    );

    const response = await fetch("http://msw.harness.invalid/lifecycle");

    await expect(response.json()).resolves.toEqual(lifecycle);
  });

  it("rejeita request inesperada em vez de deixar trafego escapar", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await expect(fetch("http://msw.harness.invalid/unhandled")).rejects.toThrow();
    expect(consoleError).toHaveBeenCalled();
  });
});
