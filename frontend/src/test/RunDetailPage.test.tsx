import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { expect, test, vi } from "vitest";

import { RunDetailPage } from "../pages/RunDetailPage";
import { ambiguousDecision, run } from "./fixtures";
import { jsonResponse, renderWithProviders } from "./render";

test("analista entende a distribuição, compara possibilidades e registra aprovação", async () => {
  const fetchMock = vi.fn(
    (input: string | URL | Request, init?: RequestInit) => {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;
      if (url.endsWith("/runs/run-demo-001")) return jsonResponse(run);
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
      if (url.includes("/decisions") && init?.method === "POST")
        return jsonResponse({ event_id: "review-1" }, 201);
      if (url.endsWith("/decisions")) return jsonResponse([ambiguousDecision]);
      return jsonResponse({ error: { message: "missing" } }, 404);
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  renderWithProviders(
    <Routes>
      <Route path="/runs/:runId" element={<RunDetailPage />} />
    </Routes>,
    "/runs/run-demo-001",
  );
  expect(
    await screen.findByText("Resultado da conciliação"),
  ).toBeInTheDocument();
  expect(screen.getByText("Distribuição da conciliação")).toBeInTheDocument();
  expect(
    await screen.findByText("Base: 3 registros participantes"),
  ).toBeInTheDocument();
  await user.click(
    await screen.findByText(
      "Há mais de uma possibilidade igualmente válida; a decisão precisa de revisão.",
    ),
  );
  expect(screen.getByText("Entenda este resultado")).toBeInTheDocument();
  expect(
    screen.getByText("Possibilidades com a mesma prioridade"),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText(/Possibilidade: origem dataset-a:A1/),
  ).toHaveLength(2);
  expect(screen.getByText("O que significa cada etiqueta")).toBeInTheDocument();
  await user.type(
    screen.getByLabelText("Motivo"),
    "Conferi a referência bancária",
  );
  await user.click(
    screen.getByRole("button", { name: "Aprovar possibilidade" }),
  );
  expect(
    await screen.findByText("Resultado da conciliação"),
  ).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/reviews"),
    expect.objectContaining({ method: "POST" }),
  );
});
