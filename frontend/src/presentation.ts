import type { MatchStatus, RunStatus } from "./types";

export const matchStatusLabels: Record<MatchStatus, string> = {
  MATCHED: "Conciliado",
  SPLIT_MATCHED: "Conciliado em grupo",
  UNMATCHED: "Sem correspondência",
  AMBIGUOUS: "Mais de uma possibilidade",
  DUPLICATE: "Possível duplicidade",
  MANUAL_REVIEW: "Revisão necessária",
};

export const runStatusLabels: Record<RunStatus, string> = {
  PENDING: "Pendente",
  QUEUED: "Na fila",
  RUNNING: "Em processamento",
  COMPLETED: "Concluída",
  FAILED: "Falhou",
};

export const statusDescriptions: Record<MatchStatus | RunStatus, string> = {
  MATCHED: "Um registro da origem corresponde a um registro do destino.",
  SPLIT_MATCHED: "Um ou mais registros formam um grupo com valor conservado.",
  UNMATCHED: "Nenhuma possibilidade ficou dentro dos limites configurados.",
  AMBIGUOUS: "Duas ou mais possibilidades têm a mesma prioridade.",
  DUPLICATE: "Há registros repetidos no mesmo lado da conciliação.",
  MANUAL_REVIEW: "A automação parou e precisa de uma decisão do analista.",
  PENDING: "A execução foi criada e aguarda processamento.",
  QUEUED: "A execução está aguardando o trabalhador disponível.",
  RUNNING: "Os registros estão sendo comparados.",
  COMPLETED: "A comparação terminou e o resultado está disponível.",
  FAILED: "A execução terminou com erro e precisa ser verificada.",
};

export const datasetSideLabels = {
  A: "Origem (A)",
  B: "Destino (B)",
} as const;

const ruleLabels: Record<string, string> = {
  standard: "Conciliação explicável padrão",
  exact_composite: "Correspondência exata",
  amount_date_tolerance: "Tolerância de valor e data",
  bounded_split: "Conciliação em grupo",
};

export function ruleLabel(ruleId: string | null | undefined) {
  if (!ruleId) return "Sem regra automática";
  return ruleLabels[ruleId] ?? "Regra personalizada";
}

export const allStatusLabels = { ...matchStatusLabels, ...runStatusLabels };

export const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export const dateFormatter = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function countByStatus(
  counts: Record<MatchStatus, number>,
  statuses: MatchStatus[],
) {
  return statuses.reduce((sum, status) => sum + counts[status], 0);
}

export function shortId(id: string, length = 18) {
  return id.length > length ? `${id.slice(0, length)}…` : id;
}

const explanationTranslations: Record<string, string> = {
  "All configured canonical fields are equal.":
    "Todos os campos canônicos configurados são iguais.",
  "Multiple equally valid candidates require manual review.":
    "Há mais de uma possibilidade igualmente válida; a decisão precisa de revisão.",
  "Amount and date are within configured tolerances.":
    "O valor e a data estão dentro dos limites configurados.",
  "A bounded group conserves the reconciled amount.":
    "Um grupo dentro dos limites conserva o valor conciliado.",
  "Canonical records are duplicated on the same dataset side.":
    "Existem registros repetidos no mesmo lado da conciliação.",
  "Candidate search reached its configured safety limit.":
    "A busca de possibilidades atingiu o limite de segurança configurado.",
  "No configured automatic rule produced a candidate.":
    "Nenhuma regra automática configurada encontrou uma possibilidade.",
};

export function translateDecisionExplanation(value: string) {
  return explanationTranslations[value] ?? value;
}

const fieldLabels: Record<string, string> = {
  amount: "valor",
  currency: "moeda",
  date: "data",
  document: "documento",
  reference: "referência",
};

export function translateEvidence(value: string) {
  const candidate = value.match(
    /^(?:candidate sources|possibilidade origens)=(.+) (?:targets|destinos)=(.+)$/,
  );
  if (candidate)
    return `Possibilidade: origem ${candidate[1]} → destino ${candidate[2]}`;
  const amount = value.match(
    /^(?:amount delta|diferença de valor) (\S+) <= (\S+)$/,
  );
  if (amount)
    return `Diferença de valor: ${amount[1]} · limite máximo ${amount[2]}`;
  const date = value.match(/^(?:date delta|diferença de data) (\S+) <= (\S+)$/);
  if (date) return `Diferença de data: ${date[1]} · limite máximo ${date[2]}`;
  const span = value.match(/^(?:date span|intervalo de datas) (\S+) <= (\S+)$/);
  if (span) return `Intervalo de datas: ${span[1]} · limite máximo ${span[2]}`;
  const group = value.match(/^(?:group size|tamanho do grupo) (\S+) <= (\S+)$/);
  if (group) return `Tamanho do grupo: ${group[1]} · limite máximo ${group[2]}`;
  const equal = value.match(/^([^:]+): (?:equal|igual)$/);
  if (equal) {
    const field = equal[1] ?? "";
    return `${fieldLabels[field] ?? field}: valores iguais`;
  }
  const duplicate = value.match(
    /^(?:duplicate count|quantidade de duplicados) (\d+)$/,
  );
  if (duplicate) return `Quantidade de registros repetidos: ${duplicate[1]}`;
  if (
    value === "bounded search limit reached" ||
    value === "limite da busca restrita atingido"
  )
    return "O limite de segurança da busca foi atingido.";
  if (value === "matching pipeline exhausted")
    return "Todas as regras configuradas foram avaliadas.";
  return value;
}

export function translateAuditDetail(value: string) {
  const approval = value.match(/^APPROVE:(.+)$/);
  if (approval) return `Aprovação registrada para a decisão ${approval[1]}.`;
  const rejection = value.match(/^REJECT:(.+)$/);
  if (rejection) return `Rejeição registrada para a decisão ${rejection[1]}.`;
  return value;
}

const apiMessageTranslations: Record<string, string> = {
  "request is invalid": "A solicitação contém dados inválidos.",
  "reconciliation profile was not found":
    "O perfil de conciliação não foi encontrado.",
  "only completed runs can be exported":
    "Somente conciliações concluídas podem ser exportadas.",
  "run datasets are unavailable":
    "As fontes de dados desta conciliação não estão disponíveis.",
  "manual decision reason is required": "Informe o motivo da decisão manual.",
  "only ambiguous or manual-review decisions can be reviewed":
    "Somente decisões ambíguas ou encaminhadas manualmente podem ser revisadas.",
};

export function translateApiMessage(value: string) {
  if (apiMessageTranslations[value]) return apiMessageTranslations[value];
  return value
    .replace(
      /^dataset (.+) was not found$/,
      "A fonte de dados $1 não foi encontrada.",
    )
    .replace(/^run (.+) was not found$/, "A execução $1 não foi encontrada.")
    .replace(
      /^decision (.+) was not found$/,
      "A decisão $1 não foi encontrada.",
    );
}
