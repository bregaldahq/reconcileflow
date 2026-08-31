import { screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { ReviewQueuePage } from "../pages/ReviewQueuePage";
import { ambiguousDecision, run } from "./fixtures";
import { jsonResponse, renderWithProviders } from "./render";

function requestUrl(input: string | URL | Request): string {
  if (typeof input === "string") return input;
  return input instanceof URL ? input.href : input.url;
}

test("pendências mostra decisões ambíguas ainda não revisadas", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const url = requestUrl(input);
      if (url.endsWith("/runs")) return jsonResponse([run]);
      if (url.endsWith("/decisions")) return jsonResponse([ambiguousDecision]);
      if (url.endsWith("/reviews")) return jsonResponse([]);
      return jsonResponse({ error: { message: "missing" } }, 404);
    }),
  );

  renderWithProviders(<ReviewQueuePage />);

  expect(
    await screen.findByText(
      "Há mais de uma possibilidade igualmente válida; a decisão precisa de revisão.",
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("1 item")).toBeInTheDocument();
});

test("pendências remove decisões que já possuem evento de revisão", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const url = requestUrl(input);
      if (url.endsWith("/runs")) return jsonResponse([run]);
      if (url.endsWith("/decisions")) return jsonResponse([ambiguousDecision]);
      if (url.endsWith("/reviews"))
        return jsonResponse([
          {
            event_id: "review-1",
            run_id: run.run_id,
            decision_id: ambiguousDecision.decision_id,
            action: "APPROVE",
            actor_id: "demo-analyst",
            reason: "Evidência conferida",
            created_at: "2026-01-01T12:01:00Z",
          },
        ]);
      return jsonResponse({ error: { message: "missing" } }, 404);
    }),
  );

  renderWithProviders(<ReviewQueuePage />);

  expect(
    await screen.findByText("Nenhuma pendência aberta"),
  ).toBeInTheDocument();
  expect(screen.getByText("0 itens")).toBeInTheDocument();
});
