export function Panel({ title, subtitle, action, children, className = '' }) {
  return (
    <div className={`glass-panel p-6 ${className}`}>
      {(title || action) && (
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            {title && <h2 className="text-lg font-semibold text-white">{title}</h2>}
            {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}
