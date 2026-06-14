import { RefreshCw } from 'lucide-react';

export function ErrorBanner({ message, onRetry, retryLabel = 'Retry' }) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
    >
      <span>{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-ghost text-red-200 shrink-0">
          <RefreshCw className="h-4 w-4" />
          {retryLabel}
        </button>
      )}
    </div>
  );
}
