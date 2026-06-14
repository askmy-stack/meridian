import { Link } from 'react-router-dom';

/**
 * Consistent page hero with eyebrow, title, subtitle, badges, and actions.
 */
export function PageHeader({
  eyebrow,
  title,
  subtitle,
  badges = [],
  actions,
  children,
  className = '',
  gradient = 'blue',
}) {
  const gradients = {
    blue: 'border-blue-500/20 from-blue-500/12 via-[rgba(15,22,41,0.95)] to-[#070b14]',
    violet: 'border-violet-500/20 from-violet-500/12 via-[rgba(15,22,41,0.95)] to-[#070b14]',
    amber: 'border-amber-500/20 from-amber-500/12 via-[rgba(15,22,41,0.95)] to-[#070b14]',
    cyan: 'border-cyan-500/20 from-cyan-500/12 via-[rgba(15,22,41,0.95)] to-[#070b14]',
  };

  const eyebrowColors = {
    blue: 'text-blue-400',
    violet: 'text-violet-400',
    amber: 'text-amber-400',
    cyan: 'text-cyan-400',
  };

  return (
    <section
      className={`relative overflow-hidden rounded-3xl border p-6 sm:p-8 lg:p-10 bg-gradient-to-br ${gradients[gradient] || gradients.blue} ${className}`}
    >
      <div className="absolute top-0 right-0 w-56 h-56 sm:w-64 sm:h-64 bg-blue-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 pointer-events-none" />
      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 flex-1 space-y-3">
          {eyebrow && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
              <p className={`text-xs font-semibold uppercase tracking-widest ${eyebrowColors[gradient] || eyebrowColors.blue}`}>
                {eyebrow}
              </p>
              {badges.map((badge) => (
                <span
                  key={badge}
                  className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-white/5 text-slate-300 border border-white/10"
                >
                  {badge}
                </span>
              ))}
            </div>
          )}
          <h1 className="page-title text-3xl sm:text-4xl lg:text-5xl leading-tight">{title}</h1>
          {subtitle && (
            <p className="text-slate-400 max-w-2xl text-base sm:text-lg leading-relaxed">{subtitle}</p>
          )}
          {children}
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 shrink-0">{actions}</div>
        )}
      </div>
    </section>
  );
}

/** Convenience wrapper for Link actions in PageHeader */
export function PageHeaderLink({ to, className = 'btn-ghost', children, ...props }) {
  return (
    <Link to={to} className={className} {...props}>
      {children}
    </Link>
  );
}
