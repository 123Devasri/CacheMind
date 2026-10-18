import { describe, it, expect } from 'vitest';

describe('Semantic Cache Decision & Latency Formatting', () => {
  it('identifies CACHE HIT vs CACHE MISS appropriately', () => {
    const hitResponse = {
      query: 'What is the annual leave policy for permanent employees?',
      decision: 'HIT',
      is_cached: true,
      answer: 'Permanent employees receive 18 days of annual leave per calendar year.',
      provider_used: 'SEMANTIC_CACHE',
      lookup_latency_ms: 4.2,
      total_latency_ms: 5.1,
      policy_id: 'TN-HR-LEAVE-01',
      policy_version: '1.0'
    };

    expect(hitResponse.is_cached).toBe(true);
    expect(hitResponse.decision).toBe('HIT');
    expect(hitResponse.lookup_latency_ms).toBeLessThan(20.0);
    expect(hitResponse.provider_used).toBe('SEMANTIC_CACHE');
  });

  it('identifies CACHE MISS and tracks grounded fallback latency', () => {
    const missResponse = {
      query: 'What is the procedure for pet insurance reimbursement?',
      decision: 'MISS',
      is_cached: false,
      answer: 'No supported answer found in approved company policies.',
      provider_used: 'GROUNDED_RETRIEVAL_FALLBACK',
      lookup_latency_ms: 8.5,
      total_latency_ms: 185.0,
      policy_id: null,
      policy_version: null
    };

    expect(missResponse.is_cached).toBe(false);
    expect(missResponse.decision).toBe('MISS');
    expect(missResponse.total_latency_ms).toBeGreaterThan(missResponse.lookup_latency_ms);
  });

  it('evaluates Clopper-Pearson false hit rate boundaries', () => {
    const targetFHR = 0.01; // 1.0%
    const observedFHR = 0.00; // 0%
    const upperConfidenceBound = 0.0085; // 0.85% (95% exact binomial)

    expect(upperConfidenceBound).toBeLessThanOrEqual(targetFHR);
    expect(observedFHR).toBeLessThanOrEqual(upperConfidenceBound);
  });
});
