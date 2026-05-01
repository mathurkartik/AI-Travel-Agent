/**
 * Plan Request Form Component
 */

import { useState } from 'react';

interface PlanFormProps {
  onSubmit: (request: string) => void;
  loading: boolean;
  disabled?: boolean;
}

const EXAMPLE_REQUESTS = [
  "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. Love food and temples, hate crowds.",
  "7 days in Italy. Rome, Florence, Venice. $4,500 budget. Art and history enthusiast.",
  "Weekend in New York City. $800 budget. Foodie, love Broadway shows.",
];

export function PlanForm({ onSubmit, loading, disabled }: PlanFormProps) {
  const [request, setRequest] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (request.trim()) {
      onSubmit(request.trim());
    }
  };

  const loadExample = (example: string) => {
    setRequest(example);
  };

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: '24px' }}>
      <div style={{ marginBottom: '16px' }}>
        <label 
          htmlFor="travel-request" 
          style={{ 
            display: 'block', 
            marginBottom: '8px', 
            fontWeight: 600 
          }}
        >
          Describe your dream trip
        </label>
        
        <textarea
          id="travel-request"
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="Where do you want to go? How long? What's your budget? What do you love? What do you want to avoid?"
          rows={4}
          disabled={loading || disabled}
          style={{
            width: '100%',
            padding: '12px',
            fontSize: '14px',
            border: '1px solid #ddd',
            borderRadius: '6px',
            resize: 'vertical',
            fontFamily: 'inherit',
          }}
        />
      </div>

      {/* Example Requests */}
      <div style={{ marginBottom: '16px' }}>
        <span style={{ fontSize: '13px', color: '#666' }}>Try an example: </span>
        {EXAMPLE_REQUESTS.map((example, index) => (
          <button
            key={index}
            type="button"
            onClick={() => loadExample(example)}
            disabled={loading || disabled}
            style={{
              fontSize: '12px',
              marginLeft: '8px',
              padding: '4px 8px',
              background: '#f0f0f0',
              border: '1px solid #ddd',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Example {index + 1}
          </button>
        ))}
      </div>

      <button
        type="submit"
        disabled={!request.trim() || loading || disabled}
        style={{
          padding: '12px 24px',
          fontSize: '16px',
          fontWeight: 600,
          background: !request.trim() || loading || disabled ? '#ccc' : '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '6px',
          cursor: !request.trim() || loading || disabled ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? (
          <>
            <span className="spinner" style={{ marginRight: '8px' }}>⏳</span>
            Planning your trip...
          </>
        ) : (
          '✨ Generate Itinerary'
        )}
      </button>
    </form>
  );
}
