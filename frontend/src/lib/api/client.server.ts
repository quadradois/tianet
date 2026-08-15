import "server-only";

import createClient from "openapi-fetch";
import type { ClientOptions } from "openapi-fetch";

import type { paths } from "./openapi.generated";

export function createBackendClient(
  baseUrl: string,
  options: Omit<ClientOptions, "baseUrl"> = {},
) {
  return createClient<paths>({ ...options, baseUrl });
}
