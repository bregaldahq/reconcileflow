import { expect, test } from "@playwright/test";

const datasets = [
  {
    dataset_id: "dataset-a",
    name: "razao.csv",
    side: "A",
    fingerprint: "a".repeat(64),
    headers: ["id", "amount", "currency", "date", "document", "reference"],
    row_count: 3,
    byte_size: 200,
    is_mapped: true,
    created_at: "2026-01-01T12:00:00Z",
  },
  {
    dataset_id: "dataset-b",
    name: "extrato.csv",
    side: "B",
    fingerprint: "b".repeat(64),
    headers: ["id", "amount", "currency", "date", "document", "reference"],
    row_count: 3,
    byte_size: 200,
    is_mapped: true,
    created_at: "2026-01-01T12:00:00Z",
  },
];

const run = {
  run_id: "run-e2e",
  dataset_a_id: "dataset-a",
  dataset_b_id: "dataset-b",
  dataset_a_fingerprint: "a".repeat(64),
  dataset_b_fingerprint: "b".repeat(64),
  rule_id: "standard",
  rule_version: "1",
  normalization_version: "br-v1",
  status: "COMPLETED",
  progress_percent: 100,
  counts: {
    MATCHED: 1,
    SPLIT_MATCHED: 1,
    UNMATCHED: 0,
    AMBIGUOUS: 1,
    DUPLICATE: 0,
    MANUAL_REVIEW: 0,
  },
  created_at: "2026-01-01T12:00:00Z",
  updated_at: "2026-01-01T12:00:01Z",
  correlation_id: "corr-e2e",
  error_code: null,
};

test("fluxo crítico chega à evidência explicável de um caso ambíguo", async ({
  page,
}) => {
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/api/v1/datasets") return route.fulfill({ json: datasets });
    if (path === "/api/v1/profiles")
      return route.fulfill({
        json: [
          {
            rule_id: "standard",
            version: "1",
            label: "Conciliação explicável padrão",
            amount_tolerance: "0.50",
            date_tolerance_days: 2,
            split_enabled: true,
          },
        ],
      });
    if (path === "/api/v1/runs" && route.request().method() === "POST")
      return route.fulfill({ status: 201, json: run });
    if (path === "/api/v1/runs") return route.fulfill({ json: [] });
    if (path === "/api/v1/runs/run-e2e") return route.fulfill({ json: run });
    if (path === "/api/v1/runs/run-e2e/decisions")
      return route.fulfill({
        json: [
          {
            decision_id: "decision-e2e",
            status: "AMBIGUOUS",
            source_ids: ["dataset-a:A1"],
            target_ids: ["dataset-b:B1", "dataset-b:B2"],
            rule_id: "amount_date_tolerance",
            rule_version: "1",
            confidence: "0.900000",
            explanation:
              "Há mais de uma possibilidade igualmente válida; a decisão precisa de revisão.",
            evidence: [
              "possibilidade origens=dataset-a:A1 destinos=dataset-b:B1",
              "possibilidade origens=dataset-a:A1 destinos=dataset-b:B2",
            ],
          },
          {
            decision_id: "decision-split",
            status: "SPLIT_MATCHED",
            source_ids: ["dataset-a:A2"],
            target_ids: ["dataset-b:B3", "dataset-b:B4"],
            rule_id: "bounded_split",
            rule_version: "1",
            confidence: "0.950000",
            explanation:
              "Um grupo dentro dos limites conserva o valor conciliado.",
            evidence: [
              "diferença de valor 0.00 <= 0.50",
              "tamanho do grupo 2 <= 4",
              "intervalo de datas 1d <= 2d",
              "currency: igual",
            ],
          },
        ],
      });
    if (path.endsWith("/reviews") && route.request().method() === "POST")
      return route.fulfill({ status: 201, json: { event_id: "review-e2e" } });
    return route.fulfill({
      status: 404,
      json: { error: { message: "não encontrado" } },
    });
  });

  await page.goto("/");
  await page
    .getByRole("main")
    .getByRole("link", { name: "Nova conciliação" })
    .click();
  await expect(page.getByText("Escolha as duas fontes")).toBeVisible();
  await page.getByRole("button", { name: /Conferir colunas/ }).click();
  await page.getByRole("button", { name: /Confirmar colunas/ }).click();
  await page.getByRole("button", { name: /Revisar configuração/ }).click();
  await page.getByRole("button", { name: /Iniciar conciliação/ }).click();
  await expect(
    page.getByRole("heading", { name: "Resultado da conciliação" }),
  ).toBeVisible();
  await page
    .getByText(
      "Há mais de uma possibilidade igualmente válida; a decisão precisa de revisão.",
    )
    .click();
  await expect(
    page.getByRole("heading", { name: "Entenda este resultado" }),
  ).toBeVisible();
  await expect(
    page.getByText("Possibilidade: origem dataset-a:A1 → destino dataset-b:B1"),
  ).toBeVisible();
  await page.getByLabel("Motivo").fill("Referência bancária conferida");
  await page.getByRole("button", { name: "Aprovar possibilidade" }).click();
  await page.getByRole("tab", { name: /Conciliados/ }).click();
  await page
    .getByText("Um grupo dentro dos limites conserva o valor conciliado.")
    .click();
  await expect(
    page.getByText("| total origem − total destino |"),
  ).toBeVisible();
});

test("a primeira ação permanece visível sem estouro horizontal em telas estreitas", async ({
  page,
}) => {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/datasets" || path === "/api/v1/runs")
      return route.fulfill({ json: [] });
    return route.fulfill({
      status: 404,
      json: { error: { message: "não encontrado" } },
    });
  });

  for (const width of [360, 768, 1280]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    await expect(
      page.getByRole("link", { name: "Selecionar arquivos" }),
    ).toBeVisible();
    const overflow = await page.evaluate<boolean>(
      "document.documentElement.scrollWidth > document.documentElement.clientWidth",
    );
    expect(overflow).toBe(false);
  }
});
