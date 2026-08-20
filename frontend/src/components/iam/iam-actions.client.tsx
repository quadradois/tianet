"use client";

import { useActionState } from "react";

import { INITIAL_IAM_ACTION_STATE, type IamActionState } from "../../lib/iam/iam-policy";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

type Action = (state: IamActionState, formData: FormData) => Promise<IamActionState>;

export type IamActionsProps = Readonly<{
  addPermissionAction: Action;
  assignPerfilAction: Action;
  createPerfilAction: Action;
  inactivatePerfilAction: Action;
  removePerfilUsuarioAction: Action;
  removePermissionAction: Action;
  renamePerfilAction: Action;
}>;

function ActionMessage({ state }: Readonly<{ state: IamActionState }>) {
  if (state.kind === "idle") return null;
  return (
    <p className={state.kind === "success" ? "text-sm text-success" : "text-sm text-destructive"} role="status">
      {state.message}{state.correlationId ? ` Correlation ID: ${state.correlationId}` : ""}
    </p>
  );
}

function useAction(action: Action) {
  return useActionState(action, INITIAL_IAM_ACTION_STATE);
}

export function IamActions(props: IamActionsProps) {
  const [createState, createForm] = useAction(props.createPerfilAction);
  const [renameState, renameForm] = useAction(props.renamePerfilAction);
  const [inactiveState, inactiveForm] = useAction(props.inactivatePerfilAction);
  const [addState, addForm] = useAction(props.addPermissionAction);
  const [removeState, removeForm] = useAction(props.removePermissionAction);
  const [assignState, assignForm] = useAction(props.assignPerfilAction);
  const [removeUserState, removeUserForm] = useAction(props.removePerfilUsuarioAction);
  return (
    <section aria-labelledby="iam-actions-title" className="grid gap-4">
      <div>
        <h2 className="text-xl font-semibold" id="iam-actions-title">Alterar acessos</h2>
        <p className="text-sm text-muted-foreground">Use os IDs exibidos nas consultas acima para ajustar perfis e permissoes.</p>
      </div>
      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <form action={createForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-create-nome">Nome do Perfil</Label>
          <Input id="iam-create-nome" maxLength={120} name="nome" required />
          <Button type="submit">Criar Perfil</Button>
          <ActionMessage state={createState} />
        </form>
        <form action={renameForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-rename-id">ID do perfil</Label>
          <Input id="iam-rename-id" name="perfil_id" required />
          <Label htmlFor="iam-rename-nome">Novo nome</Label>
          <Input id="iam-rename-nome" maxLength={120} name="nome" required />
          <Button type="submit">Renomear Perfil</Button>
          <ActionMessage state={renameState} />
        </form>
        <form action={inactiveForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-inactivate-id">ID do perfil</Label>
          <Input id="iam-inactivate-id" name="perfil_id" required />
          <Button type="submit" variant="destructive">Inativar Perfil</Button>
          <ActionMessage state={inactiveState} />
        </form>
        <form action={addForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-add-perfil">ID do perfil</Label>
          <Input id="iam-add-perfil" name="perfil_id" required />
          <Label htmlFor="iam-add-codigo">Codigo do catalogo</Label>
          <Input id="iam-add-codigo" name="codigo" required />
          <Button type="submit">Associar permissao</Button>
          <ActionMessage state={addState} />
        </form>
        <form action={removeForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-remove-perfil">ID do perfil</Label>
          <Input id="iam-remove-perfil" name="perfil_id" required />
          <Label htmlFor="iam-remove-codigo">Codigo do catalogo</Label>
          <Input id="iam-remove-codigo" name="codigo" required />
          <Button type="submit" variant="outline">Remover permissao</Button>
          <ActionMessage state={removeState} />
        </form>
        <form action={assignForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-assign-user">ID do usuario</Label>
          <Input id="iam-assign-user" name="usuario_id" required />
          <Label htmlFor="iam-assign-perfil">ID do perfil</Label>
          <Input id="iam-assign-perfil" name="perfil_id" required />
          <Button type="submit">Atribuir Perfil ao Usuario</Button>
          <ActionMessage state={assignState} />
        </form>
        <form action={removeUserForm} className="grid min-w-0 gap-3 rounded-lg border bg-card p-4">
          <Label htmlFor="iam-remove-user">ID do usuario</Label>
          <Input id="iam-remove-user" name="usuario_id" required />
          <Button type="submit" variant="outline">Remover Perfil do Usuario</Button>
          <ActionMessage state={removeUserState} />
        </form>
      </div>
    </section>
  );
}
