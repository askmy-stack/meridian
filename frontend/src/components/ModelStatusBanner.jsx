import { AlertTriangle } from 'lucide-react';
import { useApiHealth } from '../hooks/useApiHealth';

/**
 * Amber banner when the risk model is demo-calibrated (synthetic default).
 * Complements DemoBanner (Neo4j connectivity) — scores still work, but labels are honest.
 */
export function ModelStatusBanner() {
  const { data } = useApiHealth();

  const demoModel =
    data?.model?.is_demo_calibration ||
    data?.model?.model_source === 'synthetic_default' ||
    data?.calibration_status === 'demo';

  if (!demoModel) return null;

  return (
    <div className="mb-6 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4">
      <div className="flex gap-3">
        <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-semibold text-amber-200">Demo model — not production calibrated</p>
          <p className="text-amber-200/80 mt-1">
            SCRI uses an in-memory XGBoost fit on synthetic labels. Prefer risk{' '}
            <strong className="font-medium">bands</strong> (CRITICAL/HIGH/…) over exact percentages.
            Train with <code className="text-xs bg-black/30 px-1 rounded">scripts/train_risk_model.py</code>{' '}
            and deploy <code className="text-xs bg-black/30 px-1 rounded">models/risk_scorer.xgb</code> for
            validated calibration.
          </p>
        </div>
      </div>
    </div>
  );
}
