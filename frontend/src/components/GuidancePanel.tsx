import {
  Check,
  Circle,
  FileInput,
  Play,
  SearchCheck,
  SlidersHorizontal,
} from "lucide-react";
import { Link } from "react-router-dom";

const guideSteps = [
  {
    number: 1,
    title: "Preparar fontes",
    copy: "Envie os dois arquivos e confira as colunas que representam valor e data.",
    icon: FileInput,
  },
  {
    number: 2,
    title: "Comparar",
    copy: "Escolha a regra, revise os limites e inicie a conciliação.",
    icon: SlidersHorizontal,
  },
  {
    number: 3,
    title: "Resolver pendências",
    copy: "Analise casos ambíguos sem alterar a decisão automática original.",
    icon: SearchCheck,
  },
  {
    number: 4,
    title: "Exportar evidências",
    copy: "Gere a planilha e preserve as versões usadas no resultado.",
    icon: Play,
  },
];

export function GuidancePanel({
  activeStep,
  compact = false,
}: {
  activeStep: number;
  compact?: boolean;
}) {
  return (
    <aside
      id={compact ? undefined : "como-funciona"}
      className={`guidance-panel ${compact ? "guidance-panel--compact" : ""}`}
      aria-label="Como usar o ReconcileFlow"
    >
      <div className="guidance-panel__heading">
        <span>Como usar</span>
        <strong>Da origem até a evidência</strong>
      </div>
      {!compact && (
        <p className="guidance-panel__definition">
          <strong>Origem (A)</strong> é o arquivo que você controla, como o
          razão ou ERP. <strong>Destino (B)</strong> é o arquivo que confirma a
          movimentação, como o extrato bancário.
        </p>
      )}
      <ol className="guidance-steps">
        {guideSteps.map(({ number, title, copy, icon: Icon }) => {
          const done = number < activeStep;
          const current = number === activeStep;
          return (
            <li
              className={current ? "is-current" : done ? "is-done" : ""}
              key={number}
            >
              <span className="guidance-step__marker">
                {done ? (
                  <Check size={15} />
                ) : current ? (
                  <Icon size={15} />
                ) : (
                  <Circle size={12} />
                )}
              </span>
              <span>
                <strong>
                  {number}. {title}
                </strong>
                {!compact && <small>{copy}</small>}
              </span>
            </li>
          );
        })}
      </ol>
      {!compact && (
        <>
          <details className="guide-examples" open>
            <summary>Entenda os possíveis resultados</summary>
            <dl>
              <div>
                <dt>Exato ou tolerância</dt>
                <dd>
                  Campos iguais ou diferenças dentro dos limites configurados.
                </dd>
              </div>
              <div>
                <dt>Em grupo</dt>
                <dd>Dois ou mais registros conservam o valor conciliado.</dd>
              </div>
              <div>
                <dt>Pendência</dt>
                <dd>
                  Empates, duplicidades e limites de busca nunca são resolvidos
                  em silêncio.
                </dd>
              </div>
            </dl>
          </details>
          <Link className="text-link" to="/workflow">
            Abrir conciliação guiada
          </Link>
        </>
      )}
    </aside>
  );
}
