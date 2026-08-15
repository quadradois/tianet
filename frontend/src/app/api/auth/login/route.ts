import { cookies } from "next/headers";

import { createRuntimeDependencies, handleLogin } from "@/lib/bff/backend.server";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const cookieStore = await cookies();
  return handleLogin(request, cookieStore, createRuntimeDependencies());
}
