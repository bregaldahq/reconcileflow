import { buildOutcomeDistribution } from "../outcomes";
import type { Decision, MatchStatus } from "../types";

export function OutcomeDistribution({
  decisions,
  counts,
}: {
  decisions: Decision[] | undefined;
  counts: Record<MatchStatus, number>;
}) {
  const distribution = buildOutcomeDistribution(decisions, counts);
  const summary = distribution.items
    .map((item) => `${item.label}: ${item.value}`)
    .join(", ");
  return (
    <section className="outcome-distribution" aria-labelledby="outcome-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Visão do resultado</span>
          <h2 id="outcome-title">Distribuição da conciliação</h2>
        </div>
        <span className="distribution-base">
          Base: {distribution.total.toLocaleString("pt-BR")} {distribution.unit}
        </span>
      </div>
      <div className="distribution-bar" role="img" aria-label={summary}>
        {distribution.items.map(
          (item) =>
            item.value > 0 && (
              <span
                key={item.key}
                className={`distribution-bar__${item.key}`}
                style={{ width: `${item.percent}%` }}
              />
            ),
        )}
      </div>
      <dl className="distribution-legend">
        {distribution.items.map((item) => (
          <div key={item.key}>
            <dt>
              <i className={`legend-dot legend-dot--${item.key}`} />
              <span>
                <strong>{item.label}</strong>
                <small>{item.description}</small>
              </span>
            </dt>
            <dd>
              <strong>{item.value.toLocaleString("pt-BR")}</strong>
              <small>
                {item.percent.toLocaleString("pt-BR", {
                  maximumFractionDigits: 1,
                })}
                %
              </small>
            </dd>
          </div>
        ))}
      </dl>
      <p className="distribution-note">
        Cada registro participante é contado na categoria da decisão a que
        pertence. O total não representa valor monetário.
      </p>
    </section>
  );
}
