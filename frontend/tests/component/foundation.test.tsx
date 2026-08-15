import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  EmptyState,
  ErrorState,
  LoadingState,
  NotFoundState,
  PermissionDeniedState,
  SuccessState,
} from "../../src/components/foundation/feedback-state";
import { OverflowRegion } from "../../src/components/foundation/overflow-region";
import { Button } from "../../src/components/ui/button";

describe("design foundation", () => {
  it("expõe estados por papel e nome sem inferir domínio", () => {
    render(
      <div>
        <LoadingState />
        <EmptyState />
        <ErrorState />
        <SuccessState />
        <PermissionDeniedState />
        <NotFoundState />
      </div>,
    );

    expect(screen.getByRole("status", { name: "Carregando conteúdo" })).toHaveAttribute("aria-busy", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível concluir");
    expect(screen.getByText("Nenhum item disponível")).toBeInTheDocument();
    expect(screen.getByText("Operação concluída")).toBeInTheDocument();
    expect(screen.getByText("Permissão necessária")).toBeInTheDocument();
    expect(screen.getByText("Conteúdo indisponível")).toBeInTheDocument();
    expect(screen.queryByText(/tenant|carteira/i)).not.toBeInTheDocument();
  });

  it("executa a ação disponível e preserva disabled", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <div>
        <Button onClick={onClick} type="button">Executar exemplo</Button>
        <Button disabled onClick={onClick} type="button">Indisponível</Button>
      </div>,
    );

    await user.click(screen.getByRole("button", { name: "Executar exemplo" }));
    await user.click(screen.getByRole("button", { name: "Indisponível" }));

    expect(onClick).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Indisponível" })).toBeDisabled();
  });

  it("nomeia e torna a região de overflow alcançável por teclado", () => {
    render(<OverflowRegion label="Amostra larga"><div>Conteúdo</div></OverflowRegion>);

    expect(screen.getByRole("region", { name: "Amostra larga" })).toHaveAttribute("tabindex", "0");
  });
});
