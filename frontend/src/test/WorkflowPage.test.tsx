import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { expect, test, vi } from "vitest";

import { WorkflowPage } from "../pages/WorkflowPage";
import { datasetA, datasetB, run } from "./fixtures";
import { jsonResponse, renderWithProviders } from "./render";

test("fluxo guiado revisa quatro etapas antes de iniciar a execução", async () => {
  const fetchMock = vi.fn(
    (input: string | URL | Request, init?: RequestInit) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      if (url.endsWith("/datasets")) return jsonResponse([datasetA, datasetB]);
      if (url.endsWith("/profiles"))
        return jsonResponse([
          {
            rule_id: "standard",
            version: "1",
            label: "Standard explainable reconciliation",
            amount_tolerance: "0.50",
            date_tolerance_days: 2,
            split_enabled: true,
          },
        ]);
      if (url.endsWith("/runs") && init?.method === "POST")
        return jsonResponse(run, 201);
      return jsonResponse({ error: { message: "missing" } }, 404);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  renderWithProviders(
    <Routes>
      <Route path="/workflow" element={<WorkflowPage />} />
      <Route path="/runs/:runId" element={<h1>Execução aberta</h1>} />
    </Routes>,
    "/workflow",
  );

  await waitFor(() => expect(screen.getAllByText("Validado")).toHaveLength(2));
  await user.click(screen.getByRole("button", { name: /Conferir colunas/i }));
  expect(
    screen.getByText("Confira o significado das colunas"),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Confirmar colunas/i }));
  expect(
    await screen.findByText("Defina como os registros serão comparados"),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: /Revisar configuração/i }),
  );
  expect(
    screen.getByText("Revise a configuração e inicie"),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: /Iniciar conciliação/i }),
  );
  expect(await screen.findByText("Execução aberta")).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/runs",
    expect.objectContaining({ method: "POST" }),
  );
});
