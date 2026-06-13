import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Layout } from './components/Layout';
import { EntityDrawerProvider } from './context/EntityDrawerContext';
import { Dashboard } from './pages/Dashboard';
import { NetworkView } from './pages/NetworkView';
import { AlertsView } from './pages/AlertsView';
import { RiskMapView } from './pages/RiskMapView';
import { SuppliersView } from './pages/SuppliersView';
import { SimulationView } from './pages/SimulationView';
import { TimelineView } from './pages/TimelineView';
import { SectorsView } from './pages/SectorsView';
import { CopilotView } from './pages/CopilotView';
import { LoginView } from './pages/LoginView';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 2,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <EntityDrawerProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="network" element={<NetworkView />} />
              <Route path="map" element={<RiskMapView />} />
              <Route path="timeline" element={<TimelineView />} />
              <Route path="sectors" element={<SectorsView />} />
              <Route path="suppliers" element={<SuppliersView />} />
              <Route path="simulate" element={<SimulationView />} />
              <Route path="copilot" element={<CopilotView />} />
              <Route path="alerts" element={<AlertsView />} />
              <Route path="login" element={<LoginView />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </EntityDrawerProvider>
    </QueryClientProvider>
  );
}

export default App;
