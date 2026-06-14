import { useQuery } from 'react-query';
import { fetchMetricsMethodology } from '../api/client';

/** Shared SCRI methodology + calibration labels for RiskPill / tooltips. */
export function useMethodology() {
  return useQuery(['metrics-methodology'], fetchMetricsMethodology, {
    staleTime: 10 * 60_000,
    retry: 1,
  });
}

export function calibrationSublabel(methodology) {
  return (
    methodology?.display_guidance?.calibration_sublabel ??
    (methodology?.calibration_status === 'demo' ? 'Demo calibration' : 'Modelled index')
  );
}
