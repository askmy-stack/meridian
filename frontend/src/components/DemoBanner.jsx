import { AlertCircle, Terminal } from 'lucide-react';
import { useApiHealth } from '../hooks/useApiHealth';

export function DemoBanner() {
  const { data, isError } = useApiHealth();

  if (!isError && data?.neo4j === 'ok') return null;

  return (
    <div className="mb-6 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
      <div className="flex gap-3">
        <AlertCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-semibold text-amber-200">Demo data not connected</p>
          <p className="text-amber-200/80 mt-1">
            Start the Meridian stack and seed demo data to populate live risk intelligence.
          </p>
          <div className="mt-3 flex items-start gap-2 font-mono text-xs text-amber-100/90 bg-black/30 rounded-lg p-3">
            <Terminal className="h-4 w-4 shrink-0 mt-0.5" />
            <code className="whitespace-pre-wrap">
              {`docker compose up -d neo4j kafka\nmake seed-all\nuvicorn src.api.main:app --port 8002`}
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}
