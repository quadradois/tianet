import "server-only";

import { cookies } from "next/headers";

import type { OperationalContext } from "../../lib/bff/context.server";
import { createRuntimeDependencies } from "../../lib/bff/backend.server";
import { readOpenAIConnection } from "../../lib/bff/openai.server";
import { OPENAI_READ_PERMISSION, hasOpenAIPermission } from "../../lib/openai/openai-policy";
import { OpenAIBadge } from "./openai-badge";

type OpenAIBadgeLoaderProps = Readonly<{ context: OperationalContext }>;

/** Carrega o snapshot sem bloquear a renderização do restante do shell. */
export async function OpenAIBadgeLoader({ context }: OpenAIBadgeLoaderProps) {
  if (!hasOpenAIPermission(context.permissoes, OPENAI_READ_PERMISSION)) return null;
  const result = await readOpenAIConnection(await cookies(), context, createRuntimeDependencies());
  return <OpenAIBadge result={result} />;
}
