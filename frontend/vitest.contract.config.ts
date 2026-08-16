import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    clearMocks: true,
    environment: "node",
    globals: false,
    include: ["tests/contract/**/*.test.ts"],
    passWithNoTests: false,
    restoreMocks: true,
  },
});
