import { useQuery } from "@tanstack/react-query";
import { Clock3, Download, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { dateTimeFormatter, translateAuditDetail } from "../presentation";

export function AuditPage() {
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs });
  const [runId, setRunId] = useState("");
  useEffect(() => {
    if (!runId && runs.data?.[0]) setRunId(runs.data[0].run_id);
  }, [runId, runs.data]);
  const audit = useQuery({
    queryKey: ["audit", runId],
    queryFn: () => api.audit(runId),
    enabled: Boolean(runId),
  });
  return (
    <div className="page-stack">
      <section className="page-heading page-heading--action">
        <div>
          <span className="section-kicker">
            Evidência acrescentada ao histórico
          </span>
          <h1>Histórico de auditoria</h1>
          <p>
            Decisões manuais e exportações permanecem atribuíveis sem reescrever
            o resultado automático.
          </p>
        </div>
        <label className="run-selector">
          Execução
          <select
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
          >
            <option value="">Selecione uma execução</option>
            {runs.data?.map((run) => (
              <option value={run.run_id} key={run.run_id}>
                {run.run_id}
              </option>
            ))}
          </select>
        </label>
      </section>
      {(runs.error || audit.error) && (
        <ErrorBanner error={runs.error ?? audit.error} />
      )}
      <section className="panel audit-panel">
        <div className="panel__header">
          <div>
            <span className="section-kicker">Linha do tempo</span>
            <h2>Ações registradas</h2>
          </div>
        </div>
        {audit.data?.length ? (
          <ol className="audit-timeline">
            {audit.data.map((event) => (
              <li key={event.event_id}>
                <span className="audit-timeline__icon">
                  {event.event_type === "report_exported" ? (
                    <Download size={17} />
                  ) : (
                    <ShieldCheck size={17} />
                  )}
                </span>
                <span className="audit-timeline__line" />
                <span className="audit-timeline__content">
                  <strong>
                    {event.event_type === "report_exported"
                      ? "Planilha exportada"
                      : "Revisão manual registrada"}
                  </strong>
                  <p>{translateAuditDetail(event.detail)}</p>
                  <small>
                    <Clock3 size={13} />{" "}
                    {dateTimeFormatter.format(new Date(event.created_at))} ·{" "}
                    {event.actor_id}
                  </small>
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <EmptyState
            title="Nenhum evento nesta execução"
            copy="Revisões e exportações serão registradas aqui."
          />
        )}
      </section>
    </div>
  );
}
