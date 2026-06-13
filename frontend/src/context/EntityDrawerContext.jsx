import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { EntityDrawer } from '../components/EntityDrawer';

const EntityDrawerContext = createContext(null);

/**
 * Global entity inspector — open from map, network, timeline, suppliers, alerts.
 */
export function EntityDrawerProvider({ children }) {
  const [entity, setEntity] = useState(null);

  const openEntity = useCallback((payload) => {
    if (!payload) return;
    setEntity({
      id: payload.id ?? payload.entity_id ?? payload.supplier_id,
      name: payload.name ?? payload.title ?? 'Entity',
      type: payload.type ?? payload.entity_type ?? payload.layer ?? 'supplier',
      risk_score: payload.risk_score ?? payload.riskScore,
      country: payload.country ?? payload.country_iso,
      coordinates: payload.coordinates,
      ...payload,
    });
  }, []);

  const closeEntity = useCallback(() => setEntity(null), []);

  const value = useMemo(
    () => ({ entity, openEntity, closeEntity }),
    [entity, openEntity, closeEntity],
  );

  return (
    <EntityDrawerContext.Provider value={value}>
      {children}
      <EntityDrawer entity={entity} onClose={closeEntity} />
    </EntityDrawerContext.Provider>
  );
}

export function useEntityDrawer() {
  const ctx = useContext(EntityDrawerContext);
  if (!ctx) {
    throw new Error('useEntityDrawer must be used within EntityDrawerProvider');
  }
  return ctx;
}
