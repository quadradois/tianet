import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { createRuntimeDependencies } from "./backend.server";
import { loadOperationalContext } from "./context.server";

/** React cache is scoped to one server render request; no context crosses sessions. */
export const currentOperationalContext = cache(async () =>
  loadOperationalContext(await cookies(), createRuntimeDependencies()));
