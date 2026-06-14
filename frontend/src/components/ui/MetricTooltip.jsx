import { HelpCircle } from 'lucide-react';

/**
 * Accessible tooltip for SCRI / KPI methodology (hover + focus).
 */
export function MetricTooltip({ label, definition, reference, limitations }) {
  if (!definition && !limitations?.length) return null;

  return (
    <span className="relative inline-flex group/metric ml-1 align-middle">
      <button
        type="button"
        className="inline-flex rounded-full p-0.5 text-slate-500 hover:text-blue-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
        aria-label={`About ${label}`}
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-72 -translate-x-1/2 rounded-xl border border-slate-600/60 bg-[#0f1629] px-3 py-2 text-left text-xs text-slate-300 opacity-0 shadow-xl transition-opacity group-hover/metric:opacity-100 group-focus-within/metric:opacity-100"
      >
        <span className="block font-semibold text-white mb-1">{label}</span>
        {definition}
        {limitations?.length > 0 && (
          <span className="mt-2 block border-t border-slate-700/60 pt-2 text-[11px] text-amber-200/90">
            <span className="font-semibold text-amber-100">Limitations</span>
            <ul className="mt-1 list-disc pl-4 space-y-0.5">
              {limitations.slice(0, 3).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </span>
        )}
        {reference && (
          <span className="mt-2 block text-[10px] text-slate-500 truncate">{reference}</span>
        )}
      </span>
    </span>
  );
}
