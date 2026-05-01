/**
 * TypeScript types matching backend Pydantic schemas.
 * Aligned with backend/app/models/schemas.py
 */

// ============================================================================
// Enums
// ============================================================================

export type ActivityType = 'temple' | 'food' | 'museum' | 'nature' | 'shopping' | 'entertainment' | 'transport' | 'other';

export type CrowdLevel = 'low' | 'medium' | 'high' | 'unknown';

export type CostBand = 'budget' | 'moderate' | 'expensive' | 'luxury';

export type ReviewSeverity = 'blocking' | 'advisory';

export type ReviewStatus = 'pass' | 'warnings' | 'fail';

// ============================================================================
// Core Models
// ============================================================================

export interface TravelConstraints {
  destination_region: string;
  cities: string[];
  duration_days: number;
  budget_total: number;
  currency: string;
  preferences: string[];
  avoidances: string[];
  hard_requirements: string[];
  soft_preferences: string[];
  trace_id: string;
}

export interface Activity {
  id: string;
  name: string;
  city: string;
  type: ActivityType;
  estimated_duration_hours: number;
  crowd_level: CrowdLevel;
  cost_band: CostBand;
  must_do: boolean;
  rationale: string;
  address?: string;
  best_time?: string;
  less_crowded_alternative?: string;
  tags: string[];
}

export interface ActivityCatalog {
  activities: Activity[];
  per_city: Record<string, string[]>;
  neighborhood_notes: Record<string, string>;
  generated_at: string;
}

export interface LodgingPlan {
  city: string;
  nights: number;
  suggested_neighborhoods: string[];
  neighborhood_rationale: string;
  estimated_cost_per_night: CostBand;
}

export interface MovementPlan {
  from_city: string;
  to_city: string;
  mode: string;
  duration_hours: number;
  frequency?: string;
  cost_band: CostBand;
  booking_notes?: string;
}

export interface DaySlot {
  slot_index: number;
  start_time: string;
  end_time: string;
  activity_type: string;
  city: string;
  travel_time_to_next_minutes?: number;
  notes?: string;
}

export interface DaySkeleton {
  day_number: number;
  city: string;
  slots: DaySlot[];
  total_travel_time_hours: number;
  pacing_notes?: string;
}

export interface BudgetCategory {
  category: 'stay' | 'transport' | 'food' | 'activities' | 'buffer';
  estimated_total: number;
  currency: string;
  breakdown?: Record<string, number>;
  notes?: string;
}

export interface BudgetViolation {
  category: string;
  estimated: number;
  limit: number;
  over_by: number;
}

export interface SuggestedSwap {
  original_item: string;
  suggested_alternative: string;
  savings_estimate: number;
  rationale: string;
}

export interface BudgetBreakdown {
  categories: BudgetCategory[];
  grand_total: number;
  currency: string;
  within_budget: boolean;
  remaining_buffer: number;
  violations: BudgetViolation[];
  suggested_swaps: SuggestedSwap[];
  flags: string[];
  generated_at: string;
}

export interface DayItineraryItem {
  slot_index: number;
  time: string;
  activity_id?: string;
  activity_name: string;
  city: string;
  type: ActivityType;
  cost_estimate: number;
  travel_time_from_prev?: string;
  notes?: string;
}

export interface DayItinerary {
  day_number: number;
  city: string;
  items: DayItineraryItem[];
  day_summary: string;
  day_cost: number;
  lodging_area?: string;
}

export interface FinalItinerary {
  id: string;
  constraints: TravelConstraints;
  days: DayItinerary[];
  neighborhoods: Record<string, string[]>;
  logistics_summary: string;
  budget_rollup: BudgetBreakdown;
  review_status: ReviewStatus;
  review_warnings: string[];
  disclaimer: string;
  generated_at: string;
}

// ============================================================================
// API Models
// ============================================================================

export interface PlanRequest {
  request: string;
  flags?: Record<string, unknown>;
}

export interface PlanResponse {
  final_itinerary: FinalItinerary;
  constraints: TravelConstraints;
  review_summary: ReviewStatus;
  trace_id: string;
  processing_time_ms?: number;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  timestamp: string;
}
