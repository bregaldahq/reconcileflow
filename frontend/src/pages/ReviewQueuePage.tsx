import { useQueries, useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { StatusBadge } from "../components/StatusBadge";
import { ruleLabel, translateDecisionExplanation } from "../presentation";

export function ReviewQueuePage() {
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs });
  const completed =
    runs.data?.filter((run) => run.status === "COMPLETED") ?? [];
  const candidateQueries = useQueries({
    queries: completed.map((run) => ({
      queryKey: ["decisions", run.run_id, "review"],
      queryFn: async () => {
        const [decisions, reviews] = await Promise.all([
          api.decisions(run.run_id),
          api.reviews(run.run_id),
        ]);
        const reviewed = new Set(reviews.map((review) => review.decision_id));
        return {
          run,
          decisions: decisions.filter(
            (decision) =>
              (decision.status === "AMBIGUOUS" ||
                decision.status === "MANUAL_REVIEW") &&
              !reviewed.has(decision.decision_id),
          ),
        };
      },
    })),
  });
  const candidates = candidateQueries.flatMap((query) =>
    query.data
      ? query.data.decisions.map((decision) => ({
          run: query.data.run,
          decision,
        }))
      : [],
  );
  const error =
    runs.error ?? candidateQueries.find((query) => query.error)?.error;
  return (
    <div className="page-stack">
      <section className="page-heading">
        <span className="section-kicker">Julgamento do analista</span>
        <h1>Pendências</h1>
        <p>
          Possibilidades equivalentes e exceções aguardam aqui uma decisão
          explícita e justificada.
        </p>
      </section>
      {error && <ErrorBanner error={error} />}
      <section className="panel data-panel">
        <div className="panel__header">
          <div>
            <span className="section-kicker">Não resolvidos</span>
            <h2>Itens que exigem atenção</h2>
          </div>
          <span className="record-count">
            {candidates.length} {candidates.length === 1 ? "item" : "itens"}
          </span>
        </div>
        {candidates.length ? (
          <div className="review-queue-list">
            {candidates.map(({ run, decision }) => (
              <Link
                className="review-queue-row"
                to={`/runs/${run.run_id}`}
                key={`${run.run_id}-${decision.decision_id}`}
              >
                <span className="review-queue-row__main">
                  <StatusBadge status={decision.status} />
                  <strong>
                    {translateDecisionExplanation(decision.explanation)}
                  </strong>
                  <small>
                    {run.run_id} · {ruleLabel(decision.rule_id)} · versão{" "}
                    {decision.rule_version}
                  </small>
                </span>
                <span className="review-queue-row__participants">
                  <small>Registros participantes</small>
                  <strong>
                    {decision.source_ids.length + decision.target_ids.length}
                  </strong>
                </span>
                <ArrowRight size={18} />
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Nenhuma pendência aberta"
            copy="Casos ambíguos e decisões encaminhadas para revisão aparecerão aqui."
          />
        )}
      </section>
    </div>
  );
}
