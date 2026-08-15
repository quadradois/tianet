import { cookies } from "next/headers";

import { createRuntimeDependencies } from "@/lib/bff/backend.server";
import { handleContextBootstrap } from "@/lib/bff/context.server";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const cookieStore = await cookies();
  return handleContextBootstrap(request, cookieStore, createRuntimeDependencies());
}
