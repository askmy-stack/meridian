import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Layout } from './components/Layout';
import { RequireAuth } from './components/RequireAuth';
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
import { GraphHealthView } from './pages/GraphHealthView';
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

function Protected({ children }) {
  return <RequireAuth>{children}</RequireAuth>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <EntityDrawerProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Protected><Dashboard /></Protected>} />
              <Route path="network" element={<Protected><NetworkView /></Protected>} />
              <Route path="map" element={<Protected><RiskMapView /></Protected>} />
              <Route path="timeline" element={<Protected><TimelineView /></Protected>} />
              <Route path="sectors" element={<Protected><SectorsView /></Protected>} />
              <Route path="suppliers" element={<Protected><SuppliersView /></Protected>} />
              <Route path="simulate" element={<Protected><SimulationView /></Protected>} />
              <Route path="copilot" element={<Protected><CopilotView /></Protected>} />
              <Route path="ops/graph-health" element={<Protected><GraphHealthView /></Protected>} />
              <Route path="alerts" element={<Protected><AlertsView /></Protected>} />
              <Route path="login" element={<LoginView />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </EntityDrawerProvider>
    </QueryClientProvider>
  );
}

export default App;
