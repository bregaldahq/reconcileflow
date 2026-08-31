import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Database, Fingerprint, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { datasetSideLabels, dateFormatter } from "../presentation";

export function DatasetsPage() {
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  return (
    <div className="page-stack">
      <section className="page-heading page-heading--action">
        <div>
          <span className="section-kicker">Inventário de dados</span>
          <h1>Fontes de dados</h1>
          <p>
            Cada envio recebe uma impressão digital e permanece disponível como
            entrada reproduzível.
          </p>
        </div>
        <Link className="button button--primary" to="/workflow">
          <Plus size={17} /> Adicionar fontes
        </Link>
      </section>
      {datasets.error && <ErrorBanner error={datasets.error} />}
      <section className="panel data-panel">
        <div className="panel__header">
          <div>
            <span className="section-kicker">Entradas validadas</span>
            <h2>Arquivos disponíveis</h2>
          </div>
          <span className="record-count">
            {datasets.data?.length ?? 0} versões
          </span>
        </div>
        {datasets.data?.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Lado</th>
                  <th>Registros</th>
                  <th>Impressão digital</th>
                  <th>Mapeamento</th>
                  <th>Enviado em</th>
                  <th aria-label="Ações" />
                </tr>
              </thead>
              <tbody>
                {datasets.data.map((dataset) => (
                  <tr key={dataset.dataset_id}>
                    <td>
                      <span className="table-title">
                        <Database size={16} />
                        <span>
                          <strong>{dataset.name}</strong>
                          <small>{dataset.dataset_id}</small>
                        </span>
                      </span>
                    </td>
                    <td>
                      <span
                        className={`side-pill side-pill--${dataset.side.toLowerCase()}`}
                      >
                        {datasetSideLabels[dataset.side]}
                      </span>
                    </td>
                    <td>{dataset.row_count.toLocaleString()}</td>
                    <td>
                      <span className="fingerprint-cell">
                        <Fingerprint size={14} />{" "}
                        {dataset.fingerprint.slice(0, 12)}…
                      </span>
                    </td>
                    <td>
                      <span
                        className={
                          dataset.is_mapped ? "mapped-state" : "unmapped-state"
                        }
                      >
                        {dataset.is_mapped ? "Mapeado" : "Não mapeado"}
                      </span>
                    </td>
                    <td>
                      {dateFormatter.format(new Date(dataset.created_at))}
                    </td>
                    <td>
                      <Link
                        to="/workflow"
                        className="row-action"
                        aria-label={`Usar ${dataset.name}`}
                      >
                        <ArrowRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhuma fonte enviada"
            copy="Arquivos CSV e XLSX aparecerão aqui depois da validação e da geração da impressão digital."
            action={
              <Link className="button button--secondary" to="/workflow">
                Adicionar primeira fonte
              </Link>
            }
          />
        )}
      </section>
    </div>
  );
}
