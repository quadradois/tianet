import { resolve } from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": resolve("src"),
      "server-only": resolve("tests/bff/server-only-shim.ts"),
    },
  },
  test: {
    clearMocks: true,
    environment: "node",
    globals: false,
    include: ["tests/bff/**/*.test.ts"],
    passWithNoTests: false,
    restoreMocks: true,
  },
});
