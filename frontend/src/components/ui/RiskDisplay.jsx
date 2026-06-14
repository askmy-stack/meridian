import { formatRiskPercent, riskColor, riskLabel, riskPillClass } from '../../lib/risk';

/**
 * SCRI score pill — band label primary, optional calibration sublabel.
 */
export function RiskPill({
  score,
  variant = 'score',
  label,
  size = 'md',
  className = '',
  calibrationLabel,
  showPercent = true,
}) {
  const band = label ?? riskLabel(score);
  const sizeClass = size === 'sm' ? 'risk-pill-sm' : 'risk-pill-md';
  const variantClass = variant === 'category' ? 'risk-pill-category' : 'risk-pill-score';
  const sublabel = calibrationLabel ?? 'Modelled index';

  if (variant === 'category') {
    return (
      <span className={`inline-flex flex-col items-end gap-0.5 ${className}`.trim()}>
        <span
          className={`risk-pill ${sizeClass} ${variantClass} ${riskPillClass(score)}`.trim()}
          title={`SCRI band ${band}`}
        >
          {band}
        </span>
        {sublabel && <span className="text-[9px] uppercase tracking-wide text-slate-500">{sublabel}</span>}
      </span>
    );
  }

  return (
    <span className={`inline-flex flex-col items-end gap-0.5 ${className}`.trim()}>
      <span
        className={`risk-pill ${sizeClass} ${variantClass} ${riskPillClass(score)}`.trim()}
        title={showPercent ? `SCRI ${formatRiskPercent(score)}% · ${band}` : band}
      >
        {band}
      </span>
      {showPercent && (
        <span className="text-[9px] tabular-nums text-slate-500">
          {formatRiskPercent(score)}% · {sublabel}
        </span>
      )}
    </span>
  );
}

/**
 * Horizontal SCRI meter — consistent height and padding at all breakpoints.
 */
export function RiskBar({ score, className = '' }) {
  const pct = formatRiskPercent(score);

  return (
    <div
      className={`risk-bar ${className}`.trim()}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`SCRI ${pct}% · ${riskLabel(score)}`}
    >
      <div
        className="risk-bar-fill"
        style={{ width: `${pct}%`, backgroundColor: riskColor(score) }}
      />
    </div>
  );
}

/**
 * List row body: title + optional risk bar.
 */
export function RiskListBody({ title, subtitle, score, showBar = true, children }) {
  return (
    <div className="risk-list-body">
      <p className="risk-list-title">{title}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-0.5 truncate">{subtitle}</p>}
      {showBar && score != null && <RiskBar score={score} className="mt-1.5 sm:mt-2" />}
      {children}
    </div>
  );
}
