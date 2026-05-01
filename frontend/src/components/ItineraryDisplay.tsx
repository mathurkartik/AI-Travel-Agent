/**
 * Itinerary Display Component
 * Renders the final travel plan
 */

import type { PlanResponse } from '../types';

interface ItineraryDisplayProps {
  response: PlanResponse;
}

export function ItineraryDisplay({ response }: ItineraryDisplayProps) {
  const { final_itinerary, constraints, review_summary, trace_id } = response;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return '#28a745';
      case 'warnings': return '#ffc107';
      case 'fail': return '#dc3545';
      default: return '#666';
    }
  };

  return (
    <div style={{ marginTop: '24px' }}>
      {/* Header */}
      <div 
        style={{ 
          padding: '16px', 
          background: '#f8f9fa', 
          borderRadius: '8px',
          marginBottom: '16px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Your Travel Itinerary</h2>
          <span 
            style={{ 
              padding: '4px 12px', 
              borderRadius: '12px',
              background: getStatusColor(review_summary),
              color: review_summary === 'pass' ? 'white' : 'black',
              fontSize: '12px',
              fontWeight: 600,
              textTransform: 'uppercase'
            }}
          >
            {review_summary}
          </span>
        </div>
        
        <div style={{ marginTop: '12px', fontSize: '13px', color: '#666' }}>
          <span>Trace ID: </span>
          <code style={{ background: '#eee', padding: '2px 6px', borderRadius: '3px' }}>
            {trace_id}
          </code>
        </div>
      </div>

      {/* Review Warnings */}
      {final_itinerary.review_warnings && final_itinerary.review_warnings.length > 0 && (
        <div 
          style={{ 
            padding: '12px 16px',
            background: '#fff3cd',
            border: '1px solid #ffeaa7',
            borderRadius: '8px',
            marginBottom: '16px'
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '8px', color: '#856404' }}>
            ⚠️ Review Warnings
          </div>
          {final_itinerary.review_warnings.map((warning, index) => (
            <div key={index} style={{ fontSize: '13px', color: '#856404', marginBottom: '4px' }}>
              • {warning}
            </div>
          ))}
        </div>
      )}

      {/* Trip Overview */}
      <div 
        style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}
      >
        <InfoCard 
          label="Destination" 
          value={constraints.destination_region} 
        />
        <InfoCard 
          label="Cities" 
          value={constraints.cities.join(', ')} 
        />
        <InfoCard 
          label="Duration" 
          value={`${constraints.duration_days} days`} 
        />
        <InfoCard 
          label="Budget" 
          value={`$${constraints.budget_total} ${constraints.currency}`} 
        />
      </div>

      {/* Preferences & Avoidances */}
      <div style={{ marginBottom: '24px' }}>
        {constraints.preferences.length > 0 && (
          <div style={{ marginBottom: '12px' }}>
            <span style={{ fontWeight: 600 }}>Preferences: </span>
            {constraints.preferences.map(p => (
              <span 
                key={p}
                style={{ 
                  display: 'inline-block',
                  margin: '0 4px 4px 0',
                  padding: '4px 8px',
                  background: '#e3f2fd',
                  borderRadius: '4px',
                  fontSize: '13px'
                }}
              >
                {p}
              </span>
            ))}
          </div>
        )}
        
        {constraints.avoidances.length > 0 && (
          <div>
            <span style={{ fontWeight: 600 }}>Avoiding: </span>
            {constraints.avoidances.map(a => (
              <span 
                key={a}
                style={{ 
                  display: 'inline-block',
                  margin: '0 4px 4px 0',
                  padding: '4px 8px',
                  background: '#ffebee',
                  borderRadius: '4px',
                  fontSize: '13px'
                }}
              >
                {a}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Day-by-Day (when implemented) */}
      {final_itinerary.days.length > 0 ? (
        <div>
          <h3 style={{ marginBottom: '16px' }}>Day-by-Day Schedule</h3>
          {final_itinerary.days.map((day) => (
            <DayCard key={day.day_number} day={day} />
          ))}
        </div>
      ) : (
        <div 
          style={{ 
            padding: '24px', 
            textAlign: 'center',
            background: '#fff3cd',
            borderRadius: '8px',
            color: '#856404'
          }}
        >
          <p><strong>Coming in Phase 7</strong></p>
          <p>Day-by-day itinerary will be displayed here once the full orchestration is implemented.</p>
        </div>
      )}

      {/* Budget Summary */}
      <BudgetCard budget={final_itinerary.budget_rollup} />

      {/* Neighborhoods */}
      <NeighborhoodsCard neighborhoods={final_itinerary.neighborhoods} />

      {/* Disclaimer */}
      <div 
        style={{ 
          marginTop: '24px',
          padding: '12px 16px',
          background: '#fff3cd',
          borderRadius: '6px',
          fontSize: '13px',
          color: '#856404'
        }}
      >
        <strong>Disclaimer:</strong> {final_itinerary.disclaimer}
      </div>

      {/* Raw JSON (for debugging) */}
      <details style={{ marginTop: '24px' }}>
        <summary style={{ cursor: 'pointer', fontSize: '13px', color: '#666' }}>
          View Raw Response (Debug)
        </summary>
        <pre 
          style={{ 
            fontSize: '11px',
            overflow: 'auto',
            background: '#f5f5f5',
            padding: '12px',
            borderRadius: '4px'
          }}
        >
          {JSON.stringify(response, null, 2)}
        </pre>
      </details>
    </div>
  );
}

// Sub-components

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div 
      style={{ 
        padding: '12px', 
        background: 'white',
        border: '1px solid #e0e0e0',
        borderRadius: '6px'
      }}
    >
      <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>
        {label}
      </div>
      <div style={{ fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function DayCard({ day }: { day: any }) {
  return (
    <div 
      style={{ 
        marginBottom: '16px',
        padding: '16px',
        background: 'white',
        border: '1px solid #e0e0e0',
        borderRadius: '8px'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h4 style={{ margin: 0 }}>Day {day.day_number}</h4>
        <span style={{ color: '#666' }}>{day.city}</span>
      </div>
      
      {day.items.map((item: any, index: number) => (
        <div 
          key={index}
          style={{ 
            display: 'flex',
            gap: '12px',
            padding: '8px 0',
            borderBottom: index < day.items.length - 1 ? '1px solid #eee' : 'none'
          }}
        >
          <span style={{ color: '#666', fontSize: '13px', minWidth: '80px' }}>
            {item.time}
          </span>
          <div>
            <div style={{ fontWeight: 500 }}>{item.activity_name}</div>
            {item.notes && (
              <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                {item.notes}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function BudgetCard({ budget }: { budget: any }) {
  return (
    <div 
      style={{ 
        marginTop: '24px',
        padding: '16px',
        background: 'white',
        border: '1px solid #e0e0e0',
        borderRadius: '8px'
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Budget Breakdown</h3>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Total Estimated:</span>
        <span style={{ fontSize: '20px', fontWeight: 600 }}>
          ${budget.grand_total} {budget.currency}
        </span>
      </div>
      
      <div style={{ marginTop: '8px' }}>
        <span 
          style={{ 
            color: budget.within_budget ? '#28a745' : '#dc3545',
            fontWeight: 600
          }}
        >
          {budget.within_budget ? '✓ Within Budget' : '⚠ Over Budget'}
        </span>
        {budget.remaining_buffer > 0 && (
          <span style={{ marginLeft: '12px', color: '#666' }}>
            (Buffer: ${budget.remaining_buffer})
          </span>
        )}
      </div>

      {budget.violations.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          {budget.violations.map((v: any, i: number) => (
            <div key={i} style={{ color: '#dc3545', fontSize: '13px' }}>
              ⚠ {v.category}: ${v.estimated} (over by ${v.over_by})
            </div>
          ))}
        </div>
      )}

      {budget.suggested_swaps.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ fontWeight: 600, marginBottom: '8px' }}>Suggested Savings:</div>
          {budget.suggested_swaps.map((swap: any, i: number) => (
            <div key={i} style={{ fontSize: '13px', marginBottom: '4px' }}>
              💡 Swap {swap.original_item} for {swap.suggested_alternative} 
              (save ~${swap.savings_estimate})
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NeighborhoodsCard({ neighborhoods }: { neighborhoods: Record<string, string[]> }) {
  return (
    <div 
      style={{ 
        marginTop: '24px',
        padding: '16px',
        background: '#e3f2fd',
        borderRadius: '8px'
      }}
    >
      <h3 style={{ marginTop: 0, marginBottom: '16px' }}>Where to Stay</h3>
      
      {Object.entries(neighborhoods).map(([city, areas]) => (
        <div key={city} style={{ marginBottom: '12px' }}>
          <strong>{city}:</strong>{' '}
          {areas.map((area, i) => (
            <span key={area}>
              {area}{i < areas.length - 1 ? ', ' : ''}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
