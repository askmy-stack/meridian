import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  AlertTriangle,
  BarChart3,
  Bot,
  Calendar,
  Factory,
  Globe,
  Layers,
  LogIn,
  Menu,
  Network,
  Play,
  Radio,
  Shield,
  X,
} from 'lucide-react';
import { useApiHealth } from '../hooks/useApiHealth';
import { NAV_LABELS } from '../lib/uiCopy';
import { ModelStatusBanner } from './ModelStatusBanner';

const NAV_ITEMS = [
  { to: '/', label: NAV_LABELS.dashboard, icon: BarChart3, end: true },
  { to: '/network', label: NAV_LABELS.network, icon: Network },
  { to: '/map', label: NAV_LABELS.map, icon: Globe },
  { to: '/timeline', label: NAV_LABELS.timeline, icon: Calendar },
  { to: '/sectors', label: NAV_LABELS.sectors, icon: Layers },
  { to: '/suppliers', label: NAV_LABELS.suppliers, icon: Factory },
  { to: '/simulate', label: NAV_LABELS.simulate, icon: Play },
  { to: '/copilot', label: NAV_LABELS.copilot, icon: Bot },
  { to: '/alerts', label: NAV_LABELS.alerts, icon: AlertTriangle },
];

function navClass({ isActive }) {
  return isActive ? 'nav-link nav-link-active' : 'nav-link';
}

export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: health } = useApiHealth();
  const live = health?.api && health?.neo4j === 'ok';

  return (
    <div className="min-h-screen grid-bg flex">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform transition-transform duration-300 lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ background: 'linear-gradient(180deg, #0a1020 0%, #070b14 100%)' }}
      >
        <div className="flex flex-col h-full border-r border-slate-800/80">
          <div className="p-5 border-b border-slate-800/80">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-blue-500/15 border border-blue-500/30">
                <Shield className="h-7 w-7 text-blue-400" />
              </div>
              <div>
                <p className="font-bold text-lg text-white tracking-tight">Meridian</p>
                <p className="text-[10px] uppercase tracking-widest text-slate-500">Risk Intelligence</p>
              </div>
            </div>
          </div>

          <nav className="flex-1 p-3 space-y-1 overflow-y-auto" aria-label="Main">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={navClass}
                onClick={() => setMobileOpen(false)}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="p-4 border-t border-slate-800/80 space-y-3">
            <NavLink to="/ops/graph-health" className={navClass} onClick={() => setMobileOpen(false)}>
              <Radio className="h-4 w-4 shrink-0" />
              {NAV_LABELS.graphHealth}
            </NavLink>
            <div className="flex items-center gap-2 px-2">
              <Radio className={`h-3.5 w-3.5 ${live ? 'text-emerald-400' : 'text-amber-400'}`} />
              <span className="text-xs text-slate-400">
                {live ? 'Live graph connected' : 'Awaiting Neo4j'}
              </span>
              <span
                className={`ml-auto h-2 w-2 rounded-full ${
                  live ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400 animate-pulse'
                }`}
              />
            </div>
            <NavLink to="/login" className={navClass} onClick={() => setMobileOpen(false)}>
              <LogIn className="h-4 w-4" />
              Sign in
            </NavLink>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Main */}
      <div className="flex-1 lg:ml-64 min-h-screen flex flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-800/60 backdrop-blur-xl bg-[#070b14]/80">
          <div className="flex items-center justify-between px-4 sm:px-6 lg:px-8 h-14">
            <button
              type="button"
              className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="flex items-center gap-2 text-xs ml-auto">
              <span className="text-slate-500">API</span>
              <span className={health?.api ? 'text-emerald-400' : 'text-red-400'}>
                {health?.api ? 'Online' : 'Offline'}
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-8 w-full">
          <ModelStatusBanner />
          <Outlet />
        </main>
      </div>

      {mobileOpen && (
        <button
          type="button"
          className="fixed top-4 right-4 z-50 lg:hidden p-2 rounded-lg bg-slate-800 text-white"
          onClick={() => setMobileOpen(false)}
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}
