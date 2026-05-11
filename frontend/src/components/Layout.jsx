import { Link, Outlet } from 'react-router-dom';
import { AlertTriangle, BarChart3, Network, Shield } from 'lucide-react';

export function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <Shield className="h-8 w-8 text-blue-400" />
              <span className="font-bold text-xl">Meridian</span>
            </div>
            <nav className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-2 hover:text-blue-400">
                <BarChart3 className="h-5 w-5" />
                Dashboard
              </Link>
              <Link to="/network" className="flex items-center gap-2 hover:text-blue-400">
                <Network className="h-5 w-5" />
                Network
              </Link>
              <Link to="/alerts" className="flex items-center gap-2 hover:text-red-400">
                <AlertTriangle className="h-5 w-5" />
                Alerts
              </Link>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
