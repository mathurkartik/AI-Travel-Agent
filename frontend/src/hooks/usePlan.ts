/**
 * React Hook for managing plan state and API calls
 */

import { useState, useCallback } from 'react';
import { createPlan, checkHealth, ApiError } from '../services/api';
import type { PlanResponse, HealthResponse } from '../types';

interface UsePlanState {
  loading: boolean;
  error: string | null;
  traceId: string | null;
  missingFields: string[];
  suggestedTiers: Array<{ tier: string; label: string }>;
}

interface UsePlanReturn extends UsePlanState {
  submitPlan: (request: string) => Promise<PlanResponse | null>;
  checkBackendHealth: () => Promise<HealthResponse | null>;
  clearError: () => void;
}

export function usePlan(): UsePlanReturn {
  const [state, setState] = useState<UsePlanState>({
    loading: false,
    error: null,
    traceId: null,
    missingFields: [],
    suggestedTiers: [],
  });

  const submitPlan = useCallback(async (request: string): Promise<PlanResponse | null> => {
    if (!request.trim()) {
      setState(prev => ({ ...prev, error: 'Please enter a travel request' }));
      return null;
    }

    setState({ loading: true, error: null, traceId: null, missingFields: [], suggestedTiers: [] });

    try {
      const response = await createPlan({ request });
      setState({
        loading: false,
        error: null,
        traceId: response.trace_id,
        missingFields: [],
        suggestedTiers: [],
      });
      return response;
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : 'An unexpected error occurred';
      
      const traceId = err instanceof ApiError ? (err.traceId ?? null) : null;
      const missingFields = err instanceof ApiError ? err.missingFields : [];
      const suggestedTiers = err instanceof ApiError ? err.suggestedTiers : [];
      
      setState({
        loading: false,
        error: errorMessage,
        traceId,
        missingFields,
        suggestedTiers,
      });
      return null;
    }
  }, []);

  const checkBackendHealth = useCallback(async (): Promise<HealthResponse | null> => {
    try {
      const health = await checkHealth();
      return health;
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err instanceof Error ? err.message : 'Health check failed',
      }));
      return null;
    }
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    ...state,
    submitPlan,
    checkBackendHealth,
    clearError,
  };
}
