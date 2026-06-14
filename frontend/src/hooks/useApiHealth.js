import { useQuery } from 'react-query';
import { apiClient } from '../api/client';

export function useApiHealth() {
  return useQuery(
    ['api-health'],
    async () => {
      const { data } = await apiClient.get('/health');
      let neo4j = 'unknown';
      try {
        await apiClient.get('/health/neo4j');
        neo4j = 'ok';
      } catch {
        neo4j = 'down';
      }
      return {
        api: data?.status === 'healthy',
        neo4j,
        model: data?.model,
        calibration_status: data?.calibration_status,
        is_demo_calibration: data?.is_demo_calibration,
        raw: data,
      };
    },
    { refetchInterval: 30_000, retry: 1 },
  );
}
