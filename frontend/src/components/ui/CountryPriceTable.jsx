import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { riskBandColor, riskBandLabel } from '../../data/sectorIntelligence';

const BASELINE = 100;

/**
 * Sortable country price / risk table paired with RegionRiskMap.
 */
export function CountryPriceTable({ countries = [], demoLabel = 'Demo template · not live market data' }) {
  const [sortKey, setSortKey] = useState('priceIndex');
  const [sortDir, setSortDir] = useState('desc');

  const sorted = useMemo(() => {
    const list = [...countries];
    list.sort((a, b) => {
      const av = a[sortKey] ?? 0;
      const bv = b[sortKey] ?? 0;
      if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    return list;
  }, [countries, sortKey, sortDir]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ column }) => {
    if (sortKey !== column) return null;
    return sortDir === 'asc' ? (
      <ArrowUp className="h-3 w-3 inline ml-1" />
    ) : (
      <ArrowDown className="h-3 w-3 inline ml-1" />
    );
  };

  if (countries.length === 0) {
    return <p className="text-sm text-slate-500 py-6 text-center">No country price data</p>;
  }

  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-amber-200/70 mb-3">{demoLabel}</p>
      <div className="overflow-x-auto rounded-xl border border-slate-700/60">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700/60 bg-slate-900/60 text-left text-xs uppercase tracking-wider text-slate-500">
              <th className="px-4 py-3 font-semibold">
                <button type="button" onClick={() => toggleSort('name')} className="hover:text-slate-300">
                  Country
                  <SortIcon column="name" />
                </button>
              </th>
              <th className="px-4 py-3 font-semibold">
                <button type="button" onClick={() => toggleSort('riskBand')} className="hover:text-slate-300">
                  Risk band
                  <SortIcon column="riskBand" />
                </button>
              </th>
              <th className="px-4 py-3 font-semibold text-right">
                <button type="button" onClick={() => toggleSort('priceIndex')} className="hover:text-slate-300">
                  Price index
                  <SortIcon column="priceIndex" />
                </button>
              </th>
              <th className="px-4 py-3 font-semibold text-right hidden sm:table-cell">
                <button
                  type="button"
                  onClick={() => toggleSort('populationAtRisk')}
                  className="hover:text-slate-300"
                >
                  Pop. at risk (M)
                  <SortIcon column="populationAtRisk" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => {
              const delta = row.priceIndex - BASELINE;
              return (
                <tr
                  key={row.iso}
                  className="border-b border-slate-800/80 hover:bg-slate-800/30 transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="font-medium text-white">{row.name}</span>
                    <span className="text-xs text-slate-500 ml-2">{row.iso}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full border"
                      style={{
                        color: riskBandColor(row.riskBand),
                        borderColor: `${riskBandColor(row.riskBand)}55`,
                        backgroundColor: `${riskBandColor(row.riskBand)}18`,
                      }}
                    >
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: riskBandColor(row.riskBand) }}
                      />
                      {riskBandLabel(row.riskBand)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    <span className="font-semibold text-white">{row.priceIndex}</span>
                    <span
                      className={`text-xs ml-1.5 ${delta >= 0 ? 'text-red-400' : 'text-emerald-400'}`}
                    >
                      {delta >= 0 ? '+' : ''}
                      {delta}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-400 hidden sm:table-cell">
                    {row.populationAtRisk?.toFixed(1) ?? '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-600 mt-2">
        Price index baseline = {BASELINE} (portfolio reference). Modelled index bands — not exchange prices.
      </p>
    </div>
  );
}
