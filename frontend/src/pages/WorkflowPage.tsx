import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileSpreadsheet,
  Fingerprint,
  LoaderCircle,
  Play,
  Scale,
  Settings2,
  UploadCloud,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { ErrorBanner } from "../components/ErrorBanner";
import { GuidancePanel } from "../components/GuidancePanel";
import { datasetSideLabels } from "../presentation";
import type { Dataset, Profile } from "../types";

type Mapping = Parameters<typeof api.mapDataset>[1];

const canonicalFields: {
  key: keyof Mapping;
  label: string;
  description: string;
  required?: boolean;
}[] = [
  {
    key: "transaction_id",
    label: "Identificador da transação",
    description: "Código original do registro",
  },
  {
    key: "amount",
    label: "Valor",
    description: "Valor monetário da transação",
    required: true,
  },
  { key: "currency", label: "Moeda", description: "Código como BRL ou USD" },
  {
    key: "booking_date",
    label: "Data de lançamento",
    description: "Data usada na comparação",
    required: true,
  },
  {
    key: "document",
    label: "Documento",
    description: "CPF, CNPJ ou identificador fiscal",
  },
  {
    key: "reference",
    label: "Referência",
    description: "Nota, fatura ou referência bancária",
  },
];

const aliases: Record<string, string[]> = {
  transaction_id: ["id", "transaction_id", "transaction", "codigo"],
  amount: ["amount", "valor", "value", "total"],
  currency: ["currency", "moeda"],
  booking_date: ["date", "data", "booking_date"],
  document: ["document", "cpf", "cnpj", "taxpayer_id"],
  reference: ["reference", "ref", "invoice", "nota"],
};

function guessedMapping(dataset?: Dataset): Mapping {
  const headers = dataset?.headers ?? [];
  const find = (key: string) =>
    headers.find((header) => aliases[key]?.includes(header.toLowerCase())) ??
    null;
  return {
    amount: find("amount") ?? "",
    booking_date: find("booking_date") ?? "",
    currency: find("currency"),
    transaction_id: find("transaction_id"),
    source_record_id: null,
    document: find("document"),
    reference: find("reference"),
    default_currency: "BRL",
  };
}

function profileName(profile: Profile) {
  return profile.rule_id === "standard"
    ? "Conciliação explicável padrão"
    : profile.label;
}

function UploadCard({
  side,
  dataset,
  onUpload,
  busy,
}: {
  side: "A" | "B";
  dataset?: Dataset;
  onUpload: (file: File) => void;
  busy: boolean;
}) {
  const [file, setFile] = useState<File>();
  const sideName = side === "A" ? "Origem" : "Destino";
  return (
    <article className={`upload-card ${dataset ? "upload-card--ready" : ""}`}>
      <div className="upload-card__heading">
        <span className={`side-pill side-pill--${side.toLowerCase()}`}>
          {sideName} · lado {side}
        </span>
        {dataset && (
          <span className="ready-label">
            <Check size={14} /> Validado
          </span>
        )}
      </div>
      {dataset ? (
        <div className="uploaded-file">
          <span className="uploaded-file__icon">
            <FileSpreadsheet size={22} />
          </span>
          <span>
            <strong>{dataset.name}</strong>
            <small>
              {dataset.row_count.toLocaleString("pt-BR")} registros ·{" "}
              {dataset.headers.length} colunas
            </small>
            <small className="uploaded-file__fingerprint">
              <Fingerprint size={12} /> {dataset.fingerprint.slice(0, 16)}…
            </small>
          </span>
        </div>
      ) : (
        <>
          <label className="drop-zone">
            <UploadCloud size={25} />
            <strong>
              {file ? file.name : "Escolha um arquivo CSV ou XLSX"}
            </strong>
            <span>{file ? "Pronto para validar" : "Limite de 10 MB"}</span>
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => setFile(event.target.files?.[0])}
            />
          </label>
          <button
            className="button button--secondary button--full"
            disabled={!file || busy}
            onClick={() => file && onUpload(file)}
          >
            {busy ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <UploadCloud size={17} />
            )}
            Validar arquivo
          </button>
        </>
      )}
    </article>
  );
}

function MappingEditor({
  dataset,
  mapping,
  onChange,
}: {
  dataset: Dataset;
  mapping: Mapping;
  onChange: (mapping: Mapping) => void;
}) {
  return (
    <article className="mapping-card">
      <div className="mapping-card__header">
        <span className={`side-pill side-pill--${dataset.side.toLowerCase()}`}>
          {datasetSideLabels[dataset.side]}
        </span>
        <span>
          <strong>{dataset.name}</strong>
          <small>{dataset.headers.length} colunas disponíveis</small>
        </span>
      </div>
      <div className="mapping-list">
        {canonicalFields.map((field) => (
          <label key={field.key}>
            <span>
              {field.label}{" "}
              {field.required && <b aria-label="obrigatório">*</b>}
              <small>{field.description}</small>
            </span>
            <select
              value={mapping[field.key] ?? ""}
              onChange={(event) =>
                onChange({
                  ...mapping,
                  [field.key]:
                    event.target.value || (field.required ? "" : null),
                })
              }
            >
              <option value="">
                {field.required ? "Selecione uma coluna" : "Não usar"}
              </option>
              {dataset.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
    </article>
  );
}

const helpByStep = [
  {
    title: "Escolha fontes comparáveis",
    copy: "Use arquivos que representem o mesmo período ou conjunto de transações. A origem costuma ser o razão; o destino, o extrato ou arquivo do provedor.",
  },
  {
    title: "Diga o que cada coluna significa",
    copy: "Valor e data são obrigatórios. Documento e referência aumentam a precisão; o arquivo original nunca é alterado.",
  },
  {
    title: "Entenda os limites",
    copy: "A regra tenta igualdade exata, depois tolerância de valor e data. Divisões só são avaliadas quando o perfil permite.",
  },
  {
    title: "Confirme antes de executar",
    copy: "A execução registra arquivos, mapeamentos e versão da regra. Assim, o resultado pode ser reproduzido depois.",
  },
];

export function WorkflowPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const datasetsQuery = useQuery({
    queryKey: ["datasets"],
    queryFn: api.datasets,
  });
  const profiles = useQuery({ queryKey: ["profiles"], queryFn: api.profiles });
  const [step, setStep] = useState(1);
  const [datasetAId, setDatasetAId] = useState("");
  const [datasetBId, setDatasetBId] = useState("");
  const [mappingA, setMappingA] = useState<Mapping>(() => guessedMapping());
  const [mappingB, setMappingB] = useState<Mapping>(() => guessedMapping());
  const [profileIndex, setProfileIndex] = useState(0);

  const datasetA = datasetsQuery.data?.find(
    (item) => item.dataset_id === datasetAId,
  );
  const datasetB = datasetsQuery.data?.find(
    (item) => item.dataset_id === datasetBId,
  );
  const selectedProfile = profiles.data?.[profileIndex];

  useEffect(() => {
    if (!datasetAId) {
      const existing = datasetsQuery.data?.find(
        (item) => item.side === "A" && item.is_mapped,
      );
      if (existing) setDatasetAId(existing.dataset_id);
    }
    if (!datasetBId) {
      const existing = datasetsQuery.data?.find(
        (item) => item.side === "B" && item.is_mapped,
      );
      if (existing) setDatasetBId(existing.dataset_id);
    }
  }, [datasetAId, datasetBId, datasetsQuery.data]);

  useEffect(() => setMappingA(guessedMapping(datasetA)), [datasetA]);
  useEffect(() => setMappingB(guessedMapping(datasetB)), [datasetB]);

  const upload = useMutation({
    mutationFn: ({ side, file }: { side: "A" | "B"; file: File }) =>
      api.upload(side, file),
    onSuccess: (dataset) => {
      queryClient.setQueryData<Dataset[]>(["datasets"], (current = []) => [
        ...current,
        dataset,
      ]);
      if (dataset.side === "A") setDatasetAId(dataset.dataset_id);
      else setDatasetBId(dataset.dataset_id);
    },
  });

  const mapping = useMutation({
    mutationFn: async () => {
      if (!datasetA || !datasetB)
        throw new Error("Selecione as duas fontes antes de continuar.");
      const mappedA = datasetA.is_mapped
        ? datasetA
        : await api.mapDataset(datasetA.dataset_id, mappingA);
      const mappedB = datasetB.is_mapped
        ? datasetB
        : await api.mapDataset(datasetB.dataset_id, mappingB);
      return [mappedA, mappedB];
    },
    onSuccess: (mapped) => {
      queryClient.setQueryData<Dataset[]>(["datasets"], (current = []) =>
        current.map(
          (item) =>
            mapped.find(
              (candidate) => candidate.dataset_id === item.dataset_id,
            ) ?? item,
        ),
      );
      setStep(3);
    },
  });

  const start = useMutation({
    mutationFn: async () => {
      if (!datasetA || !datasetB || !selectedProfile)
        throw new Error("Complete as quatro etapas antes de iniciar.");
      return api.startRun(
        datasetA.dataset_id,
        datasetB.dataset_id,
        selectedProfile,
      );
    },
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      void navigate(`/runs/${run.run_id}`);
    },
  });

  const error =
    datasetsQuery.error ??
    profiles.error ??
    upload.error ??
    mapping.error ??
    start.error;
  const mappingsValid = Boolean(
    mappingA.amount &&
    mappingA.booking_date &&
    mappingB.amount &&
    mappingB.booking_date,
  );
  const bothReady = Boolean(datasetA && datasetB);
  const steps = useMemo(
    () => [
      { number: 1, label: "Escolher fontes", icon: UploadCloud },
      { number: 2, label: "Conferir colunas", icon: Settings2 },
      { number: 3, label: "Definir comparação", icon: Scale },
      { number: 4, label: "Revisar e iniciar", icon: Play },
    ],
    [],
  );

  const stepHeading = [
    "",
    "Escolha as duas fontes",
    "Confira o significado das colunas",
    "Defina como os registros serão comparados",
    "Revise a configuração e inicie",
  ];

  return (
    <div className="page-stack workflow-page">
      <section className="page-heading">
        <span className="section-kicker">Conciliação guiada</span>
        <h1>Nova conciliação</h1>
        <p>
          Quatro etapas para transformar dois arquivos em um resultado
          explicável e reproduzível.
        </p>
      </section>
      <GuidancePanel activeStep={step <= 2 ? 1 : 2} compact />
      <ol className="stepper" aria-label="Etapas da conciliação">
        {steps.map(({ number, label, icon: Icon }) => (
          <li
            className={
              number === step
                ? "stepper__active"
                : number < step
                  ? "stepper__done"
                  : ""
            }
            key={number}
            aria-current={number === step ? "step" : undefined}
          >
            <span>
              {number < step ? <Check size={16} /> : <Icon size={15} />}
            </span>
            <strong>
              {number}. {label}
            </strong>
          </li>
        ))}
      </ol>
      {error && (
        <ErrorBanner
          error={error}
          onDismiss={() => {
            upload.reset();
            mapping.reset();
            start.reset();
          }}
        />
      )}

      <div className="workflow-layout">
        <section className="workflow-surface">
          <div className="workflow-surface__header">
            <div>
              <span className="section-kicker">Etapa {step} de 4</span>
              <h2>{stepHeading[step]}</h2>
            </div>
          </div>

          {step === 1 && (
            <>
              <div className="existing-selectors">
                <label>
                  Fonte de origem
                  <select
                    value={datasetAId}
                    onChange={(event) => setDatasetAId(event.target.value)}
                  >
                    <option value="">Enviar novo arquivo</option>
                    {datasetsQuery.data
                      ?.filter((item) => item.side === "A")
                      .map((item) => (
                        <option value={item.dataset_id} key={item.dataset_id}>
                          {item.name} · {item.row_count} registros
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Fonte de destino
                  <select
                    value={datasetBId}
                    onChange={(event) => setDatasetBId(event.target.value)}
                  >
                    <option value="">Enviar novo arquivo</option>
                    {datasetsQuery.data
                      ?.filter((item) => item.side === "B")
                      .map((item) => (
                        <option value={item.dataset_id} key={item.dataset_id}>
                          {item.name} · {item.row_count} registros
                        </option>
                      ))}
                  </select>
                </label>
              </div>
              <div className="upload-grid">
                <UploadCard
                  side="A"
                  dataset={datasetA}
                  busy={upload.isPending}
                  onUpload={(file) => upload.mutate({ side: "A", file })}
                />
                <UploadCard
                  side="B"
                  dataset={datasetB}
                  busy={upload.isPending}
                  onUpload={(file) => upload.mutate({ side: "B", file })}
                />
              </div>
              <div className="workflow-actions">
                <span />
                <button
                  className="button button--primary"
                  disabled={!bothReady}
                  onClick={() => setStep(2)}
                >
                  Conferir colunas <ArrowRight size={17} />
                </button>
              </div>
            </>
          )}

          {step === 2 && datasetA && datasetB && (
            <>
              <div className="mapping-intro">
                <strong>Campos obrigatórios: valor e data.</strong>
                <span>
                  As sugestões foram preenchidas pelos nomes das colunas;
                  confirme antes de seguir.
                </span>
              </div>
              <div className="mapping-grid">
                <MappingEditor
                  dataset={datasetA}
                  mapping={mappingA}
                  onChange={setMappingA}
                />
                <MappingEditor
                  dataset={datasetB}
                  mapping={mappingB}
                  onChange={setMappingB}
                />
              </div>
              <div className="workflow-actions">
                <button
                  className="button button--ghost"
                  onClick={() => setStep(1)}
                >
                  <ArrowLeft size={17} /> Voltar
                </button>
                <button
                  className="button button--primary"
                  disabled={!mappingsValid || mapping.isPending}
                  onClick={() => mapping.mutate()}
                >
                  {mapping.isPending && (
                    <LoaderCircle className="spin" size={17} />
                  )}{" "}
                  Confirmar colunas <ArrowRight size={17} />
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <div className="profile-explanation">
                <strong>A regra trabalha em camadas</strong>
                <ol>
                  <li>Compara campos exatos</li>
                  <li>Aplica tolerância de valor e data</li>
                  <li>Encaminha empates para revisão</li>
                </ol>
              </div>
              <div className="profile-grid">
                {profiles.data?.map((profile, index) => (
                  <button
                    type="button"
                    key={`${profile.rule_id}-${profile.version}`}
                    className={`profile-card ${profileIndex === index ? "profile-card--selected" : ""}`}
                    onClick={() => setProfileIndex(index)}
                    aria-pressed={profileIndex === index}
                  >
                    <span className="profile-card__radio">
                      {profileIndex === index && <Check size={13} />}
                    </span>
                    <span>
                      <small>
                        Perfil de comparação · versão {profile.version}
                      </small>
                      <strong>{profileName(profile)}</strong>
                      <p>
                        Correspondência exata → tolerância de valor/data →{" "}
                        {profile.split_enabled
                          ? "conciliação em grupo"
                          : "revisão manual"}
                      </p>
                      <span className="profile-facts">
                        Valor ± {profile.amount_tolerance} · Data ±{" "}
                        {profile.date_tolerance_days} dias
                      </span>
                    </span>
                  </button>
                ))}
              </div>
              <div className="workflow-actions">
                <button
                  className="button button--ghost"
                  onClick={() => setStep(2)}
                >
                  <ArrowLeft size={17} /> Voltar
                </button>
                <button
                  className="button button--primary"
                  disabled={!selectedProfile}
                  onClick={() => setStep(4)}
                >
                  Revisar configuração <ArrowRight size={17} />
                </button>
              </div>
            </>
          )}

          {step === 4 && datasetA && datasetB && selectedProfile && (
            <>
              <div className="review-summary">
                <div className="review-summary__flow">
                  <span>
                    <small>Origem</small>
                    <strong>{datasetA.name}</strong>
                    <em>
                      {datasetA.row_count.toLocaleString("pt-BR")} registros
                    </em>
                  </span>
                  <ArrowRight size={18} />
                  <span>
                    <small>Regra</small>
                    <strong>{profileName(selectedProfile)}</strong>
                    <em>v{selectedProfile.version}</em>
                  </span>
                  <ArrowRight size={18} />
                  <span>
                    <small>Destino</small>
                    <strong>{datasetB.name}</strong>
                    <em>
                      {datasetB.row_count.toLocaleString("pt-BR")} registros
                    </em>
                  </span>
                </div>
                <dl className="configuration-list">
                  <div>
                    <dt>Colunas obrigatórias</dt>
                    <dd>
                      {mappingA.amount} + {mappingA.booking_date} ↔{" "}
                      {mappingB.amount} + {mappingB.booking_date}
                    </dd>
                  </div>
                  <div>
                    <dt>Tolerância de valor</dt>
                    <dd>± {selectedProfile.amount_tolerance}</dd>
                  </div>
                  <div>
                    <dt>Tolerância de data</dt>
                    <dd>± {selectedProfile.date_tolerance_days} dias</dd>
                  </div>
                  <div>
                    <dt>Conciliação em grupo</dt>
                    <dd>
                      {selectedProfile.split_enabled ? "Ativada" : "Desativada"}
                    </dd>
                  </div>
                  <div>
                    <dt>Impressão digital da origem</dt>
                    <dd>
                      <code>{datasetA.fingerprint.slice(0, 24)}…</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Impressão digital do destino</dt>
                    <dd>
                      <code>{datasetB.fingerprint.slice(0, 24)}…</code>
                    </dd>
                  </div>
                </dl>
              </div>
              <div className="preflight-note">
                <Check size={17} />
                <span>
                  <strong>Configuração pronta para ser registrada</strong>Os As
                  impressões digitais, os mapeamentos e a versão da regra
                  acompanharão o resultado e a exportação.
                </span>
              </div>
              <div className="workflow-actions">
                <button
                  className="button button--ghost"
                  onClick={() => setStep(3)}
                >
                  <ArrowLeft size={17} /> Voltar
                </button>
                <button
                  className="button button--primary"
                  disabled={start.isPending}
                  onClick={() => start.mutate()}
                >
                  {start.isPending ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : (
                    <Play size={17} />
                  )}{" "}
                  Iniciar conciliação
                </button>
              </div>
            </>
          )}
        </section>
        <aside className="contextual-help">
          <span className="section-kicker">Ajuda desta etapa</span>
          <h3>{helpByStep[step - 1]?.title}</h3>
          <p>{helpByStep[step - 1]?.copy}</p>
          <strong>Ao terminar</strong>
          <p>
            {step === 4
              ? "Você será levado ao resultado e verá o progresso da execução."
              : `Você avançará para “${steps[step]?.label}”.`}
          </p>
        </aside>
      </div>
    </div>
  );
}
