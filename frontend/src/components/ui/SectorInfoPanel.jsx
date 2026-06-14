import { AlertTriangle, Globe, Users } from 'lucide-react';
import { SECTOR_PROFILES } from '../../data/sectorIntelligence';
import { DEMO_SECTOR_NOTE } from '../../lib/uiCopy';

/**
 * Sector context: strategic importance and human impact if disrupted.
 */
export function SectorInfoPanel({ sectorKey, classificationMethod = 'keyword' }) {
  const profile = SECTOR_PROFILES[sectorKey];
  if (!profile) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
      <div className="rounded-xl border border-slate-700/50 bg-slate-900/40 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Globe className="h-4 w-4 text-violet-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Why it matters</p>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{profile.whyImportant}</p>
      </div>
      <div className="rounded-xl border border-slate-700/50 bg-slate-900/40 p-4">
        <div className="flex items-center gap-2 mb-2">
          <Users className="h-4 w-4 text-amber-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">People impact</p>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{profile.peopleImpact}</p>
      </div>
      <div className="rounded-xl border border-slate-700/50 bg-slate-900/40 p-4">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Exposure</p>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">{profile.globalExposure}</p>
        {classificationMethod && (
          <p className="text-[10px] text-amber-200/60 mt-2 uppercase tracking-wider">
            {DEMO_SECTOR_NOTE}
          </p>
        )}
      </div>
    </div>
  );
}
