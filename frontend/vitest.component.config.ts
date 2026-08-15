import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    clearMocks: true,
    environment: "jsdom",
    globals: false,
    include: ["tests/component/**/*.test.tsx"],
    passWithNoTests: false,
    restoreMocks: true,
    setupFiles: ["./tests/component/setup.ts"],
  },
});
