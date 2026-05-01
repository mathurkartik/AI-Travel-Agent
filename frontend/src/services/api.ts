/**
 * API Service Layer
 * Handles all backend communication
 */

import type { PlanRequest, PlanResponse, HealthResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public traceId?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Check backend health status
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  
  if (!response.ok) {
    throw new ApiError(
      `Health check failed: ${response.statusText}`,
      response.status,
      response.headers.get('X-Trace-ID') || undefined
    );
  }
  
  return response.json();
}

/**
 * Submit travel plan request
 */
export async function createPlan(request: PlanRequest): Promise<PlanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  
  const traceId = response.headers.get('X-Trace-ID') || undefined;
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      errorData.error || `Request failed: ${response.statusText}`,
      response.status,
      traceId || errorData.trace_id
    );
  }
  
  const data = await response.json();
  return {
    ...data,
    trace_id: data.trace_id || traceId,
  };
}

/**
 * Get plan by ID (Phase 10: persistent storage)
 */
export async function getPlan(planId: string): Promise<PlanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/plan/${planId}`);
  
  if (!response.ok) {
    throw new ApiError(
      `Failed to fetch plan: ${response.statusText}`,
      response.status
    );
  }
  
  return response.json();
}

export { ApiError };
