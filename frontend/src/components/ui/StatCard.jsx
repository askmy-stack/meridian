export function StatCard({ icon, title, value, subtitle, accent = 'blue', trend }) {
  const accents = {
    blue: 'from-blue-500/20 to-blue-600/5 text-blue-400',
    red: 'from-red-500/20 to-red-600/5 text-red-400',
    green: 'from-emerald-500/20 to-emerald-600/5 text-emerald-400',
    purple: 'from-violet-500/20 to-violet-600/5 text-violet-400',
    amber: 'from-amber-500/20 to-amber-600/5 text-amber-400',
  };

  return (
    <div className="stat-card group">
      <div className="flex items-start justify-between">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${accents[accent] || accents.blue}`}>
          {icon}
        </div>
        {trend != null && (
          <span className="text-xs font-medium text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded-lg">
            {trend}
          </span>
        )}
      </div>
      <p className="mt-4 text-sm text-slate-400">{title}</p>
      <p className="mt-1 text-3xl font-bold text-white tracking-tight">{value}</p>
      {subtitle && <p className="mt-2 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
}
