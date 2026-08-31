import { expect, test } from "vitest";

import {
  datasetSideLabels,
  matchStatusLabels,
  ruleLabel,
  runStatusLabels,
  statusDescriptions,
  translateApiMessage,
  translateAuditDetail,
  translateDecisionExplanation,
  translateEvidence,
} from "../presentation";

test("rótulos em português cobrem os enums estáveis da API", () => {
  expect(matchStatusLabels).toEqual({
    MATCHED: "Conciliado",
    SPLIT_MATCHED: "Conciliado em grupo",
    UNMATCHED: "Sem correspondência",
    AMBIGUOUS: "Mais de uma possibilidade",
    DUPLICATE: "Possível duplicidade",
    MANUAL_REVIEW: "Revisão necessária",
  });
  expect(Object.keys(runStatusLabels)).toEqual([
    "PENDING",
    "QUEUED",
    "RUNNING",
    "COMPLETED",
    "FAILED",
  ]);
  expect(datasetSideLabels).toEqual({ A: "Origem (A)", B: "Destino (B)" });
  expect(statusDescriptions.AMBIGUOUS).toContain("mesma prioridade");
  expect(ruleLabel("amount_date_tolerance")).toBe("Tolerância de valor e data");
  expect(ruleLabel(null)).toBe("Sem regra automática");
});

test("retornos legados em inglês são apresentados em português", () => {
  expect(
    translateDecisionExplanation(
      "Multiple equally valid candidates require manual review.",
    ),
  ).toContain("decisão precisa de revisão");
  expect(
    translateEvidence(
      "candidate sources=origem:A1 targets=destino:B1,destino:B2",
    ),
  ).toBe("Possibilidade: origem origem:A1 → destino destino:B1,destino:B2");
  expect(translateEvidence("amount delta 0.25 <= 0.50")).toBe(
    "Diferença de valor: 0.25 · limite máximo 0.50",
  );
  expect(translateEvidence("date delta 1d <= 2d")).toBe(
    "Diferença de data: 1d · limite máximo 2d",
  );
  expect(translateEvidence("date span 2d <= 3d")).toBe(
    "Intervalo de datas: 2d · limite máximo 3d",
  );
  expect(translateEvidence("group size 2 <= 4")).toBe(
    "Tamanho do grupo: 2 · limite máximo 4",
  );
  expect(translateEvidence("currency: equal")).toBe("moeda: valores iguais");
  expect(translateEvidence("duplicate count 2")).toBe(
    "Quantidade de registros repetidos: 2",
  );
  expect(translateEvidence("bounded search limit reached")).toContain(
    "limite de segurança",
  );
  expect(translateEvidence("matching pipeline exhausted")).toContain(
    "regras configuradas",
  );
  expect(translateAuditDetail("APPROVE:decisão-1")).toContain(
    "Aprovação registrada",
  );
  expect(translateAuditDetail("REJECT:decisão-1")).toContain(
    "Rejeição registrada",
  );
  expect(translateApiMessage("request is invalid")).toBe(
    "A solicitação contém dados inválidos.",
  );
  expect(translateApiMessage("run run-1 was not found")).toBe(
    "A execução run-1 não foi encontrada.",
  );
});
