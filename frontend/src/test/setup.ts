import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

Object.defineProperty(globalThis, "crypto", {
  value: { randomUUID: () => "00000000-0000-4000-8000-000000000001" },
  configurable: true,
});
