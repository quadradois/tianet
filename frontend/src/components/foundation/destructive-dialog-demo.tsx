"use client";

import { Button } from "../ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";

function DestructiveDialogDemo() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button type="button" variant="destructive">Revisar ação destrutiva</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirmar intenção</DialogTitle>
          <DialogDescription>
            Este exemplo técnico demonstra foco contido, Escape e retorno ao acionador. Nenhum comando de produto é enviado.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">Cancelar</Button>
          </DialogClose>
          <DialogClose asChild>
            <Button type="button" variant="destructive">Confirmar exemplo</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export { DestructiveDialogDemo };
