import type { Decision, MatchStatus } from "./types";

type OutcomeKey = "matched" | "review" | "unmatched";

const groups: {
  key: OutcomeKey;
  label: string;
  description: string;
  statuses: MatchStatus[];
}[] = [
  {
    key: "matched",
    label: "Conciliados",
    description: "Exatos, por tolerância ou em grupo",
    statuses: ["MATCHED", "SPLIT_MATCHED"],
  },
  {
    key: "review",
    label: "Pendências",
    description: "Ambíguos, duplicados ou revisão necessária",
    statuses: ["AMBIGUOUS", "DUPLICATE", "MANUAL_REVIEW"],
  },
  {
    key: "unmatched",
    label: "Sem correspondência",
    description: "Nenhuma possibilidade dentro da regra",
    statuses: ["UNMATCHED"],
  },
];

export function buildOutcomeDistribution(
  decisions: Decision[] | undefined,
  counts: Record<MatchStatus, number>,
) {
  const usingParticipants = decisions !== undefined;
  const values = groups.map((group) => {
    const value = usingParticipants
      ? decisions
          .filter((decision) => group.statuses.includes(decision.status))
          .reduce(
            (sum, decision) =>
              sum +
              new Set([...decision.source_ids, ...decision.target_ids]).size,
            0,
          )
      : group.statuses.reduce((sum, status) => sum + counts[status], 0);
    return { ...group, value };
  });
  const total = values.reduce((sum, item) => sum + item.value, 0);
  return {
    total,
    unit: usingParticipants ? "registros participantes" : "decisões",
    items: values.map((item) => ({
      key: item.key,
      label: item.label,
      description: item.description,
      value: item.value,
      percent: total ? (item.value / total) * 100 : 0,
    })),
  };
}
