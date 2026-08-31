import { describe, expect, test } from "vitest";

import { buildOutcomeDistribution } from "../outcomes";
import type { Decision, MatchStatus } from "../types";

const emptyCounts: Record<MatchStatus, number> = {
  MATCHED: 2,
  SPLIT_MATCHED: 1,
  UNMATCHED: 1,
  AMBIGUOUS: 1,
  DUPLICATE: 0,
  MANUAL_REVIEW: 0,
};

describe("distribuição do resultado", () => {
  test("usa decisões como denominador enquanto os participantes não carregaram", () => {
    const result = buildOutcomeDistribution(undefined, emptyCounts);
    expect(result.unit).toBe("decisões");
    expect(result.total).toBe(5);
    expect(result.items.map((item) => item.value)).toEqual([3, 1, 1]);
  });

  test("troca explicitamente para registros participantes sem misturar unidades", () => {
    const decisions: Decision[] = [
      {
        decision_id: "matched",
        status: "MATCHED",
        source_ids: ["a:1"],
        target_ids: ["b:1"],
        rule_id: "exact",
        rule_version: "1",
        confidence: "1",
        explanation: "",
        evidence: [],
      },
      {
        decision_id: "ambiguous",
        status: "AMBIGUOUS",
        source_ids: ["a:2"],
        target_ids: ["b:2", "b:3"],
        rule_id: "tolerance",
        rule_version: "1",
        confidence: "0.9",
        explanation: "",
        evidence: [],
      },
    ];
    const result = buildOutcomeDistribution(decisions, emptyCounts);
    expect(result.unit).toBe("registros participantes");
    expect(result.total).toBe(5);
    expect(result.items.map((item) => item.value)).toEqual([2, 3, 0]);
    expect(result.items.reduce((sum, item) => sum + item.percent, 0)).toBe(100);
  });
});
