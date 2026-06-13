export function riskColor(score) {
  if (score >= 0.8) return '#ef4444';
  if (score >= 0.6) return '#f97316';
  if (score >= 0.4) return '#f59e0b';
  if (score >= 0.2) return '#3b82f6';
  return '#10b981';
}

export function riskLabel(score) {
  if (score >= 0.8) return 'CRITICAL';
  if (score >= 0.6) return 'HIGH';
  if (score >= 0.4) return 'MEDIUM';
  if (score >= 0.2) return 'LOW';
  return 'MINIMAL';
}

export function riskPillClass(score) {
  if (score >= 0.8) return 'bg-red-500/20 text-red-300 border border-red-500/30';
  if (score >= 0.6) return 'bg-orange-500/20 text-orange-300 border border-orange-500/30';
  if (score >= 0.4) return 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
  if (score >= 0.2) return 'bg-blue-500/20 text-blue-300 border border-blue-500/30';
  return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
}
