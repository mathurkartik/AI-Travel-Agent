/**
 * Error Display Component
 */

interface ErrorDisplayProps {
  message: string;
  traceId?: string | null;
  onDismiss?: () => void;
}

export function ErrorDisplay({ message, traceId, onDismiss }: ErrorDisplayProps) {
  return (
    <div 
      style={{ 
        padding: '16px',
        background: '#ffebee',
        border: '1px solid #ef5350',
        borderRadius: '8px',
        marginBottom: '16px'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 600, color: '#c62828', marginBottom: '8px' }}>
            ⚠️ Error
          </div>
          <div style={{ color: '#c62828' }}>{message}</div>
          
          {traceId && (
            <div style={{ marginTop: '8px', fontSize: '13px' }}>
              <span style={{ color: '#666' }}>Trace ID: </span>
              <code style={{ background: 'rgba(0,0,0,0.05)', padding: '2px 6px', borderRadius: '3px' }}>
                {traceId}
              </code>
            </div>
          )}
        </div>
        
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#c62828',
              padding: '0 4px',
            }}
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}
