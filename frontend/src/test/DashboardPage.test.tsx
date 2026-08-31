import { screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { DashboardPage } from "../pages/DashboardPage";
import { datasetA, datasetB, run } from "./fixtures";
import { jsonResponse, renderWithProviders } from "./render";

test("home prioritizes review attention and keeps recent work visible", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      if (url.endsWith("/datasets")) return jsonResponse([datasetA, datasetB]);
      if (url.endsWith("/runs")) return jsonResponse([run]);
      return jsonResponse({ error: { message: "missing" } }, 404);
    }),
  );
  renderWithProviders(<DashboardPage />);
  const runReferences = await screen.findAllByText("run-demo-001");
  expect(runReferences.length).toBeGreaterThan(0);
  expect(screen.getByText("1 item precisa da sua análise")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Nova conciliação/i }),
  ).toHaveAttribute("href", "/workflow");
});

test("home explains the first action when the workspace is empty", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => jsonResponse([])),
  );
  renderWithProviders(<DashboardPage />);
  expect(
    await screen.findByText("Nenhuma conciliação executada"),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Iniciar primeira conciliação" }),
  ).toBeInTheDocument();
});
