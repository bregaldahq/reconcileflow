import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Download,
  Fingerprint,
  LoaderCircle,
  Scale,
  SearchCheck,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { OutcomeDistribution } from "../components/OutcomeDistribution";
import { StatusBadge } from "../components/StatusBadge";
import { StatusGuide } from "../components/StatusGuide";
import {
  ruleLabel,
  shortId,
  translateDecisionExplanation,
  translateEvidence,
} from "../presentation";
import type { Decision, MatchStatus, Profile } from "../types";

const tabs: { label: string; statuses: MatchStatus[] }[] = [
  { label: "Todos", statuses: [] },
  { label: "Para revisar", statuses: ["AMBIGUOUS", "MANUAL_REVIEW"] },
  { label: "Duplicidades", statuses: ["DUPLICATE"] },
  { label: "Conciliados", statuses: ["MATCHED", "SPLIT_MATCHED"] },
  { label: "Sem correspondência", statuses: ["UNMATCHED"] },
];

function ParticipantList({ ids }: { ids: string[] }) {
  if (!ids.length) return <span className="muted-cell">Nenhum</span>;
  return (
    <span className="participant-list">
      {ids.map((id) => (
        <code key={id}>{id.split(":").at(-1)}</code>
      ))}
    </span>
  );
}

function EvidenceFlow({ decision }: { decision: Decision }) {
  const sourceLabel =
    decision.source_ids.length === 1
      ? "1 registro"
      : `${decision.source_ids.length} registros`;
  const targetLabel =
    decision.target_ids.length === 1
      ? "1 registro"
      : `${decision.target_ids.length} registros`;
  return (
    <div
      className="evidence-flow"
      aria-label="Origem, regra e destino desta decisão"
    >
      <div>
        <small>Origem</small>
        <strong>{sourceLabel}</strong>
        <ParticipantList ids={decision.source_ids} />
      </div>
      <ArrowRight size={17} aria-hidden="true" />
      <div className="evidence-flow__rule">
        <small>Regra aplicada</small>
        <strong>{ruleLabel(decision.rule_id)}</strong>
        <span>
          {decision.rule_version
            ? `versão ${decision.rule_version}`
            : "encaminhamento do fluxo de análise"}
        </span>
      </div>
      <ArrowRight size={17} aria-hidden="true" />
      <div>
        <small>Destino</small>
        <strong>{targetLabel}</strong>
        <ParticipantList ids={decision.target_ids} />
      </div>
    </div>
  );
}

function CandidateMatrix({ decision }: { decision: Decision }) {
  if (decision.status !== "AMBIGUOUS" || decision.target_ids.length < 2)
    return null;
  const source = decision.source_ids[0]?.split(":").at(-1) ?? "—";
  return (
    <div className="candidate-matrix">
      <h3>Possibilidades com a mesma prioridade</h3>
      <div className="candidate-matrix__header">
        <span>Origem</span>
        <span>Destino possível</span>
        <span>Conclusão</span>
      </div>
      {decision.target_ids.map((target) => (
        <div className="candidate-matrix__row" key={target}>
          <code>{source}</code>
          <code>{target.split(":").at(-1)}</code>
          <span>Exige julgamento</span>
        </div>
      ))}
      <p>
        Nenhuma opção foi escolhida automaticamente porque a regra produziu
        possibilidades equivalentes.
      </p>
    </div>
  );
}

function EvidenceLayout({ decision }: { decision: Decision }) {
  const exactFields = decision.evidence
    .filter((item) => /: (?:equal|igual)$/.test(item))
    .map((item) => item.replace(/: (?:equal|igual)$/, ""));
  const amountEvidence = decision.evidence.find((item) =>
    /^(?:amount delta|diferença de valor) \S+ <= \S+$/.test(item),
  );
  const amountMatch = amountEvidence?.match(
    /^(?:amount delta|diferença de valor) (\S+) <= (\S+)$/,
  );
  const dateEvidence = decision.evidence.find((item) =>
    /^(?:date (?:delta|span)|diferença de data|intervalo de datas) \S+ <= \S+$/.test(
      item,
    ),
  );
  const dateMatch = dateEvidence?.match(
    /^(?:date (?:delta|span)|diferença de data|intervalo de datas) (\S+) <= (\S+)$/,
  );

  if (decision.status === "DUPLICATE") {
    const participants = [...decision.source_ids, ...decision.target_ids];
    return (
      <div className="duplicate-layout">
        <strong>Grupo possivelmente duplicado</strong>
        <p>
          Os {participants.length} registros abaixo compartilham a mesma chave
          canônica no mesmo lado.
        </p>
        <ParticipantList ids={participants} />
      </div>
    );
  }

  if (!exactFields.length && !amountMatch && !dateMatch) return null;
  return (
    <div className="measurement-layout">
      {decision.status === "SPLIT_MATCHED" && amountMatch && (
        <div className="split-equation">
          <small>Conservação do grupo</small>
          <span>| total origem − total destino |</span>
          <strong>
            = {amountMatch[1]} ≤ {amountMatch[2]}
          </strong>
        </div>
      )}
      <dl>
        {amountMatch && decision.status !== "SPLIT_MATCHED" && (
          <div>
            <dt>Diferença de valor</dt>
            <dd>
              <strong>{amountMatch[1]}</strong>
              <span>limite ≤ {amountMatch[2]}</span>
            </dd>
          </div>
        )}
        {dateMatch && (
          <div>
            <dt>Diferença de data</dt>
            <dd>
              <strong>{dateMatch[1]}</strong>
              <span>limite ≤ {dateMatch[2]}</span>
            </dd>
          </div>
        )}
        {exactFields.length > 0 && (
          <div>
            <dt>Campos alinhados</dt>
            <dd className="exact-field-list">
              {exactFields.map((field) => (
                <span key={field}>
                  <Check size={12} />
                  {translateEvidence(`${field}: igual`).split(":")[0]}
                </span>
              ))}
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}

function DecisionDrawer({
  runId,
  decision,
  profile,
  onClose,
}: {
  runId: string;
  decision: Decision;
  profile?: Profile;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  const review = useMutation({
    mutationFn: (action: "APPROVE" | "REJECT") =>
      api.review(runId, decision.decision_id, action, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["audit", runId] });
      void queryClient.invalidateQueries({ queryKey: ["decisions", runId] });
      void queryClient.invalidateQueries({ queryKey: ["reviews", runId] });
      onClose();
    },
  });
  const reviewable =
    decision.status === "AMBIGUOUS" || decision.status === "MANUAL_REVIEW";
  const confidence = decision.confidence
    ? Number(decision.confidence) * 100
    : null;
  return (
    <>
      <button
        className="drawer-backdrop"
        onClick={onClose}
        aria-label="Fechar detalhe"
      />
      <aside
        className="decision-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="decision-title"
      >
        <div className="decision-drawer__header">
          <div>
            <span className="section-kicker">Evidência da decisão</span>
            <h2 id="decision-title">Entenda este resultado</h2>
          </div>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Fechar detalhe"
          >
            <X size={20} />
          </button>
        </div>
        <div className="drawer-section drawer-section--summary">
          <StatusBadge status={decision.status} />
          <p>{translateDecisionExplanation(decision.explanation)}</p>
        </div>
        <div className="drawer-section">
          <h3>Como os registros foram avaliados</h3>
          <EvidenceFlow decision={decision} />
          {profile && (
            <dl className="rule-limits">
              <div>
                <dt>Limite de valor</dt>
                <dd>± {profile.amount_tolerance}</dd>
              </div>
              <div>
                <dt>Limite de data</dt>
                <dd>± {profile.date_tolerance_days} dias</dd>
              </div>
              <div>
                <dt>Grupos</dt>
                <dd>
                  {profile.split_enabled ? "Permitidos" : "Não permitidos"}
                </dd>
              </div>
            </dl>
          )}
        </div>
        <CandidateMatrix decision={decision} />
        <div className="drawer-section">
          <div className="evidence-heading">
            <h3>Evidências registradas pela regra</h3>
            {confidence !== null && (
              <span>
                Confiança{" "}
                {confidence.toLocaleString("pt-BR", {
                  maximumFractionDigits: 1,
                })}
                %
              </span>
            )}
          </div>
          <EvidenceLayout decision={decision} />
          {decision.evidence.length ? (
            <ul className="evidence-list">
              {decision.evidence.map((item) => (
                <li key={item}>
                  <Check size={15} />
                  <span>{translateEvidence(item)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="evidence-empty">
              A decisão não possui evidências adicionais além dos participantes
              e da regra.
            </p>
          )}
          {decision.status === "SPLIT_MATCHED" && (
            <p className="conservation-note">
              <Scale size={15} /> Grupo conservado entre{" "}
              {decision.source_ids.length} registro(s) de origem e{" "}
              {decision.target_ids.length} de destino.
            </p>
          )}
        </div>
        {reviewable && (
          <div className="drawer-section review-form">
            <h3>Registrar julgamento do analista</h3>
            <p>
              Sua decisão será acrescentada ao histórico. O resultado automático
              original não será reescrito.
            </p>
            <label>
              Motivo
              <textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Descreva a evidência que você conferiu…"
              />
            </label>
            {review.error && <ErrorBanner error={review.error} />}
            <div className="review-actions">
              <button
                className="button button--danger"
                disabled={!reason.trim() || review.isPending}
                onClick={() => review.mutate("REJECT")}
              >
                Recusar possibilidade
              </button>
              <button
                className="button button--primary"
                disabled={!reason.trim() || review.isPending}
                onClick={() => review.mutate("APPROVE")}
              >
                {review.isPending && (
                  <LoaderCircle className="spin" size={16} />
                )}{" "}
                Aprovar possibilidade
              </button>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const [activeTab, setActiveTab] = useState(0);
  const [selected, setSelected] = useState<Decision>();
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.run(runId),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      query.state.data?.status === "QUEUED" ||
      query.state.data?.status === "RUNNING"
        ? 1500
        : false,
  });
  const decisions = useQuery({
    queryKey: ["decisions", runId],
    queryFn: () => api.decisions(runId),
    enabled: run.data?.status === "COMPLETED",
  });
  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: api.profiles,
    enabled: run.data?.status === "COMPLETED",
  });
  const exportMutation = useMutation({
    mutationFn: () => api.exportReport(runId),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `reconcileflow-${runId}.xlsx`;
      anchor.click();
      URL.revokeObjectURL(url);
    },
  });
  const filtered = useMemo(() => {
    const statuses = tabs[activeTab]?.statuses ?? [];
    return (
      decisions.data?.filter(
        (item) => !statuses.length || statuses.includes(item.status),
      ) ?? []
    );
  }, [activeTab, decisions.data]);

  if (run.isLoading)
    return (
      <div className="center-loader">
        <LoaderCircle className="spin" />
      </div>
    );
  if (run.error || !run.data)
    return (
      <ErrorBanner
        error={run.error ?? new Error("A execução não foi encontrada.")}
      />
    );
  const data = run.data;
  const totalDecisions = Object.values(data.counts).reduce(
    (sum, count) => sum + count,
    0,
  );
  const reviewCount = data.counts.AMBIGUOUS + data.counts.MANUAL_REVIEW;
  const pendingCount = reviewCount + data.counts.DUPLICATE;
  const selectedProfile = profiles.data?.find(
    (profile) =>
      profile.rule_id === data.rule_id && profile.version === data.rule_version,
  );

  const openReview = () => {
    setActiveTab(1);
    requestAnimationFrame(() =>
      document
        .getElementById("decision-list")
        ?.scrollIntoView({ behavior: "smooth", block: "start" }),
    );
  };

  return (
    <div className="page-stack run-page">
      <section className="run-heading">
        <div>
          <Link className="back-link" to="/">
            <ArrowLeft size={15} /> Voltar ao início
          </Link>
          <div className="run-title-line">
            <h1>Resultado da conciliação</h1>
            <StatusBadge status={data.status} />
          </div>
          <p>{data.run_id}</p>
        </div>
        {data.status === "COMPLETED" && (
          <button
            className="button button--secondary"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate()}
          >
            {exportMutation.isPending ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <Download size={17} />
            )}{" "}
            Exportar XLSX
          </button>
        )}
      </section>
      {(exportMutation.error || decisions.error) && (
        <ErrorBanner error={exportMutation.error ?? decisions.error} />
      )}

      {data.status !== "COMPLETED" ? (
        <section className="panel progress-panel">
          <span className="progress-panel__icon">
            <Scale size={25} />
          </span>
          <h2>
            {data.status === "FAILED"
              ? "Não foi possível concluir a execução"
              : "A conciliação está em processamento"}
          </h2>
          <p>
            {data.status === "FAILED"
              ? `Código do erro: ${data.error_code ?? "não informado"}`
              : "Você pode permanecer nesta tela; o resultado será atualizado automaticamente."}
          </p>
          <div className="progress-track">
            <span style={{ width: `${data.progress_percent}%` }} />
          </div>
          <small>{data.progress_percent}% concluído</small>
        </section>
      ) : (
        <>
          <section
            className={`result-next-action ${pendingCount ? "result-next-action--attention" : "result-next-action--resolved"}`}
          >
            <span className="result-next-action__icon">
              {pendingCount ? <SearchCheck size={21} /> : <Check size={21} />}
            </span>
            <div>
              <span className="section-kicker">Próxima ação</span>
              <h2>
                {pendingCount
                  ? `${pendingCount} ${pendingCount === 1 ? "item precisa" : "itens precisam"} de atenção`
                  : "A conciliação não possui pendências abertas"}
              </h2>
              <p>
                {pendingCount
                  ? "Revise primeiro as possibilidades equivalentes e as duplicidades antes de exportar a evidência final."
                  : "Confira a distribuição abaixo e exporte a planilha de evidências quando estiver pronto."}
              </p>
            </div>
            {pendingCount ? (
              <button className="button button--primary" onClick={openReview}>
                Revisar pendências <ArrowRight size={17} />
              </button>
            ) : (
              <button
                className="button button--primary"
                onClick={() => exportMutation.mutate()}
              >
                <Download size={17} /> Exportar evidências
              </button>
            )}
          </section>

          <OutcomeDistribution
            decisions={decisions.data}
            counts={data.counts}
          />

          {pendingCount > 0 && (
            <section
              className="exception-overview"
              aria-labelledby="exception-title"
            >
              <div className="section-heading">
                <div>
                  <span className="section-kicker">Exceções</span>
                  <h2 id="exception-title">O que impede o encerramento</h2>
                </div>
              </div>
              <div className="exception-list">
                <button onClick={() => setActiveTab(1)}>
                  <span>
                    <strong>
                      Mais de uma possibilidade ou revisão necessária
                    </strong>
                    <small>
                      A regra preservou o empate para julgamento do analista.
                    </small>
                  </span>
                  <b>{reviewCount}</b>
                  <ChevronRight size={16} />
                </button>
                <button onClick={() => setActiveTab(2)}>
                  <span>
                    <strong>Possíveis duplicidades</strong>
                    <small>
                      Registros repetidos devem ser verificados antes do aceite.
                    </small>
                  </span>
                  <b>{data.counts.DUPLICATE}</b>
                  <ChevronRight size={16} />
                </button>
              </div>
            </section>
          )}

          <section className="panel result-panel" id="decision-list">
            <div className="result-table-heading">
              <div>
                <span className="section-kicker">Detalhamento</span>
                <h2>Decisões da conciliação</h2>
              </div>
              <span>{totalDecisions.toLocaleString("pt-BR")} decisões</span>
            </div>
            <StatusGuide />
            <div
              className="result-tabs"
              role="tablist"
              aria-label="Filtrar decisões por resultado"
            >
              {tabs.map((tab, index) => (
                <button
                  role="tab"
                  aria-selected={activeTab === index}
                  className={activeTab === index ? "result-tab--active" : ""}
                  onClick={() => setActiveTab(index)}
                  key={tab.label}
                >
                  {tab.label}
                  <span>
                    {tab.statuses.length
                      ? tab.statuses.reduce(
                          (sum, status) => sum + data.counts[status],
                          0,
                        )
                      : totalDecisions}
                  </span>
                </button>
              ))}
            </div>
            {decisions.isLoading ? (
              <div className="center-loader">
                <LoaderCircle className="spin" />
              </div>
            ) : filtered.length ? (
              <div className="table-scroll">
                <table className="data-table result-table">
                  <thead>
                    <tr>
                      <th>Resultado</th>
                      <th>Origem</th>
                      <th>Destino</th>
                      <th>Regra</th>
                      <th>Confiança</th>
                      <th>Explicação</th>
                      <th aria-label="Abrir" />
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((decision) => (
                      <tr
                        key={decision.decision_id}
                        onClick={() => setSelected(decision)}
                        tabIndex={0}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            setSelected(decision);
                          }
                        }}
                      >
                        <td>
                          <StatusBadge status={decision.status} />
                        </td>
                        <td>
                          <ParticipantList ids={decision.source_ids} />
                        </td>
                        <td>
                          <ParticipantList ids={decision.target_ids} />
                        </td>
                        <td>
                          <span className="rule-cell">
                            {ruleLabel(decision.rule_id)}
                            <small>
                              {decision.rule_version &&
                                `v${decision.rule_version}`}
                            </small>
                          </span>
                        </td>
                        <td>
                          {decision.confidence
                            ? `${(Number(decision.confidence) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`
                            : "—"}
                        </td>
                        <td className="explanation-cell">
                          {translateDecisionExplanation(decision.explanation)}
                        </td>
                        <td>
                          <ChevronRight size={16} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="Nenhuma decisão nesta categoria"
                copy="Escolha outro filtro para inspecionar o resultado."
              />
            )}
          </section>

          <section className="reproducibility-section">
            <div>
              <span className="section-kicker">Reprodutibilidade</span>
              <h2>Configuração registrada com o resultado</h2>
              <p>
                Use estes dados para comprovar quais fontes e regras produziram
                a conciliação.
              </p>
            </div>
            <dl>
              <div>
                <dt>Impressão digital da origem</dt>
                <dd>
                  <Fingerprint size={14} />{" "}
                  {shortId(data.dataset_a_fingerprint, 20)}
                </dd>
              </div>
              <div>
                <dt>Impressão digital do destino</dt>
                <dd>
                  <Fingerprint size={14} />{" "}
                  {shortId(data.dataset_b_fingerprint, 20)}
                </dd>
              </div>
              <div>
                <dt>Regra</dt>
                <dd>
                  <Scale size={14} /> {ruleLabel(data.rule_id)} · versão{" "}
                  {data.rule_version}
                </dd>
              </div>
              <div>
                <dt>Normalização</dt>
                <dd>{data.normalization_version}</dd>
              </div>
            </dl>
            <button
              className="button button--secondary"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate()}
            >
              <Download size={17} /> Exportar planilha completa
            </button>
          </section>
        </>
      )}
      {selected && (
        <DecisionDrawer
          runId={runId}
          decision={selected}
          profile={selectedProfile}
          onClose={() => setSelected(undefined)}
        />
      )}
    </div>
  );
}
