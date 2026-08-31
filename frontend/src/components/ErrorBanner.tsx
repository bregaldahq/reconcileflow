import { AlertTriangle, X } from "lucide-react";

import { ApiError } from "../api";

export function ErrorBanner({
  error,
  onDismiss,
}: {
  error: unknown;
  onDismiss?: () => void;
}) {
  const message =
    error instanceof Error
      ? error.message
      : "Algo deu errado. Tente novamente.";
  const correlation = error instanceof ApiError ? error.correlationId : null;
  return (
    <div className="error-banner" role="alert">
      <AlertTriangle size={19} />
      <span>
        <strong>Não foi possível concluir esta ação.</strong>
        {message}
        {correlation && correlation !== "unknown" && (
          <small>Referência: {correlation}</small>
        )}
      </span>
      {onDismiss && (
        <button
          className="icon-button"
          onClick={onDismiss}
          aria-label="Fechar aviso"
        >
          <X size={17} />
        </button>
      )}
    </div>
  );
}
