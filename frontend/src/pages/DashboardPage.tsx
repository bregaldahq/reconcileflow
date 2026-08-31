import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  FileInput,
  LoaderCircle,
  Play,
  SearchCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { GuidancePanel } from "../components/GuidancePanel";
import { StatusBadge } from "../components/StatusBadge";
import {
  countByStatus,
  dateTimeFormatter,
  ruleLabel,
  shortId,
} from "../presentation";
import type { Run } from "../types";

function RunDistribution({ run }: { run: Run }) {
  const matched = countByStatus(run.counts, ["MATCHED", "SPLIT_MATCHED"]);
  const review = countByStatus(run.counts, [
    "AMBIGUOUS",
    "MANUAL_REVIEW",
    "DUPLICATE",
  ]);
  const unmatched = run.counts.UNMATCHED;
  const total = matched + review + unmatched;
  if (!total) return <span className="muted-cell">Aguardando resultados</span>;
  return (
    <span
      className="mini-distribution"
      aria-label={`${matched} conciliadas, ${review} pendentes e ${unmatched} sem correspondência`}
    >
      <i
        className="segment--matched"
        style={{ width: `${(matched / total) * 100}%` }}
      />
      <i
        className="segment--review"
        style={{ width: `${(review / total) * 100}%` }}
      />
      <i
        className="segment--unmatched"
        style={{ width: `${(unmatched / total) * 100}%` }}
      />
    </span>
  );
}

export function DashboardPage() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs });
  const latest = runs.data?.[0];
  const mapped =
    datasets.data?.filter((dataset) => dataset.is_mapped).length ?? 0;
  const attention =
    runs.data?.reduce(
      (sum, run) =>
        sum +
        countByStatus(run.counts, ["AMBIGUOUS", "MANUAL_REVIEW", "DUPLICATE"]),
      0,
    ) ?? 0;
  const processing = runs.data?.find(
    (run) => run.status === "QUEUED" || run.status === "RUNNING",
  );

  const nextAction =
    mapped < 2
      ? {
          step: 1,
          icon: FileInput,
          label: "Preparar fontes",
          title: "Escolha os dois arquivos que serão comparados",
          copy: "Você vai identificar as colunas de valor e data antes de executar qualquer regra.",
          to: "/workflow",
          action: "Selecionar arquivos",
        }
      : processing
        ? {
            step: 2,
            icon: LoaderCircle,
            label: "Comparação em andamento",
            title: "Acompanhe o processamento da conciliação",
            copy: `A execução está em ${processing.progress_percent}%. O resultado será atualizado automaticamente.`,
            to: `/runs/${processing.run_id}`,
            action: "Acompanhar execução",
          }
        : attention > 0
          ? {
              step: 3,
              icon: SearchCheck,
              label: "Resolver pendências",
              title: `${attention} ${attention === 1 ? "item precisa" : "itens precisam"} da sua análise`,
              copy: "Comece pelos casos com mais de uma possibilidade e registre o motivo da decisão.",
              to: "/review",
              action: "Abrir pendências",
            }
          : {
              step: latest ? 4 : 2,
              icon: Play,
              label: latest ? "Ciclo concluído" : "Comparar",
              title: latest
                ? "O ciclo atual está resolvido"
                : "As fontes estão prontas para comparar",
              copy: latest
                ? "Exporte as evidências ou inicie uma nova conciliação quando receber arquivos atualizados."
                : "Revise a regra e inicie sua primeira conciliação.",
              to: latest ? `/runs/${latest.run_id}` : "/workflow",
              action: latest
                ? "Ver resultado e exportar"
                : "Definir comparação",
            };
  const NextIcon = nextAction.icon;
  const error = datasets.error ?? runs.error;

  return (
    <div className="page-stack dashboard-page">
      <section className="page-heading page-heading--action">
        <div>
          <span className="section-kicker">Área de trabalho</span>
          <h1>Conciliação financeira</h1>
          <p>
            Compare sua origem — como razão ou ERP — com o destino que confirma
            o pagamento, como extrato bancário ou arquivo do provedor.
          </p>
        </div>
        <Link className="button button--primary" to="/workflow">
          Nova conciliação <ArrowRight size={17} />
        </Link>
      </section>

      {error && <ErrorBanner error={error} />}
      <section className="dashboard-first-view">
        <article className="next-action-panel">
          <div className="next-action-panel__label">
            <NextIcon className={processing ? "spin" : ""} size={17} />{" "}
            {nextAction.label}
          </div>
          <div>
            <span className="section-kicker">O que fazer agora</span>
            <h2>{nextAction.title}</h2>
            <p>{nextAction.copy}</p>
            {mapped < 2 && (
              <span className="accepted-formats">
                Formatos aceitos: CSV e XLSX · uma fonte de origem e uma de
                destino
              </span>
            )}
          </div>
          <Link className="button button--primary" to={nextAction.to}>
            {nextAction.action} <ArrowRight size={17} />
          </Link>
          <dl className="operational-facts">
            <div>
              <dt>Fontes prontas</dt>
              <dd>{mapped}</dd>
            </div>
            <div>
              <dt>Execuções</dt>
              <dd>{runs.data?.length ?? 0}</dd>
            </div>
            <div>
              <dt>Pendências</dt>
              <dd>{attention}</dd>
            </div>
          </dl>
        </article>
        <GuidancePanel activeStep={nextAction.step} />
      </section>

      <section className="workbook-section">
        <div className="section-heading">
          <div>
            <span className="section-kicker">Histórico recente</span>
            <h2>Últimas conciliações</h2>
          </div>
          {attention > 0 && (
            <Link className="text-link" to="/review">
              Ver todas as pendências <ArrowRight size={15} />
            </Link>
          )}
        </div>
        {runs.isLoading ? (
          <div className="loading-lines" aria-label="Carregando conciliações">
            <span />
            <span />
            <span />
          </div>
        ) : runs.data?.length ? (
          <div
            className="run-table"
            role="table"
            aria-label="Últimas conciliações"
          >
            <div className="run-table__header" role="row">
              <span>Execução</span>
              <span>Resultado</span>
              <span>Atualização</span>
              <span>Status</span>
              <span />
            </div>
            {runs.data.slice(0, 6).map((run) => (
              <Link
                className="run-table__row"
                to={`/runs/${run.run_id}`}
                key={run.run_id}
                role="row"
              >
                <span>
                  <strong>{shortId(run.run_id, 24)}</strong>
                  <small>
                    {ruleLabel(run.rule_id)} · versão {run.rule_version}
                  </small>
                </span>
                <RunDistribution run={run} />
                <time dateTime={run.updated_at}>
                  {dateTimeFormatter.format(new Date(run.updated_at))}
                </time>
                <StatusBadge status={run.status} />
                <ArrowRight size={16} />
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Nenhuma conciliação executada"
            copy="O primeiro resultado aparecerá aqui depois que você comparar duas fontes."
            action={
              <Link className="button button--secondary" to="/workflow">
                Iniciar primeira conciliação
              </Link>
            }
          />
        )}
      </section>
    </div>
  );
}
