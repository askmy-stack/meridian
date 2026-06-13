import { describe, expect, it } from 'vitest';
import { riskColor, riskLabel, riskPillClass } from './risk';

describe('risk helpers', () => {
  it('labels critical scores', () => {
    expect(riskLabel(0.85)).toBe('CRITICAL');
    expect(riskColor(0.85)).toBe('#ef4444');
    expect(riskPillClass(0.85)).toContain('red');
  });

  it('labels low scores', () => {
    expect(riskLabel(0.1)).toBe('MINIMAL');
    expect(riskColor(0.1)).toBe('#10b981');
  });
});
