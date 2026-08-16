import { cookies } from "next/headers";

import { createRuntimeDependencies, handleLogout } from "@/lib/bff/backend.server";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const cookieStore = await cookies();
  return handleLogout(request, cookieStore, createRuntimeDependencies());
}
