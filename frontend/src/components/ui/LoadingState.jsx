export function LoadingState({ label = 'Loading intelligence…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <div className="relative">
        <div className="h-14 w-14 rounded-full border-2 border-blue-500/20" />
        <div className="absolute inset-0 h-14 w-14 rounded-full border-2 border-transparent border-t-blue-500 animate-spin" />
      </div>
      <p className="text-sm text-slate-400 animate-pulse-glow">{label}</p>
    </div>
  );
}
