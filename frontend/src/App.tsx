/**
 * AI Travel Planner - Frontend App (Modern UI)
 * Phase 9: Updated UI matching tour-booking design
 */

import { useState } from 'react';
import { usePlan } from './hooks';
import type { PlanResponse } from './types';
import './App.css';

// Icons as SVG components
const GlobeIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
  </svg>
);

const SearchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.35-4.35"/>
  </svg>
);

const HeartIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
  </svg>
);

const StarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
  </svg>
);

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);

const ClockIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
);

const MapPinIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>
    <circle cx="12" cy="10" r="3"/>
  </svg>
);

const ArrowRightIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M5 12h14"/>
    <path d="m12 5 7 7-7 7"/>
  </svg>
);

const AIAgentIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a3 3 0 0 0-3 3v14a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
    <path d="M12 8h.01"/>
    <path d="M11 12h2"/>
    <path d="M12 16v.01"/>
  </svg>
);

const BuildingIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 22V9a3 3 0 0 1 3-3h6a3 3 0 0 1 3 3v13"/>
    <path d="M9 22v-4h6v4"/>
    <path d="M10 9h4"/>
    <path d="M10 13h4"/>
    <path d="M4 22h16"/>
  </svg>
);

const UtensilsIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/>
    <path d="M7 2v20"/>
    <path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/>
  </svg>
);

// Mock data for homepage
const POPULAR_DESTINATIONS = [
  {
    id: 1,
    name: 'New York City',
    description: 'Experience the bustling streets, iconic landmarks, and vibrant arts scene of the Big Apple. Perfect for foodies, art lovers, and urban explorers.',
    rating: 4.9,
    price: 450,
    image: 'https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=600',
  },
  {
    id: 2,
    name: 'Paris',
    description: 'Discover the city of love, famous for its cafe culture, haute couture, and landmarks like the Louvre and Eiffel Tower.',
    rating: 4.8,
    price: 520,
    image: 'https://images.unsplash.com/photo-1499856871958-5b9627545d1a?w=600',
  },
  {
    id: 3,
    name: 'Tokyo',
    description: 'A mesmerizing mix of ultramodern and the traditional, from neon-lit skyscrapers to historic temples.',
    rating: 4.9,
    price: 680,
    image: 'https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=600',
  },
];



function App() {
  const [view, setView] = useState<'home' | 'result'>('home');
  const [response, setResponse] = useState<PlanResponse | null>(null);
  const [requestText, setRequestText] = useState('');
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [loadingStep, setLoadingStep] = useState(0);
  const [bookingForm, setBookingForm] = useState({ name: '', email: '', comment: '' });
  const [bookingStatus, setBookingStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null);
  const [bookingLoading, setBookingLoading] = useState(false);
  const { loading, error, traceId, submitPlan, checkBackendHealth, clearError } = usePlan();

  // Progress step simulation for long LLM calls
  const LOADING_STEPS = [
    '🔍 Extracting your travel constraints...',
    '🗺️ Destination agent researching attractions...',
    '🚆 Logistics agent planning routes & stays...',
    '💰 Budget agent calculating costs...',
    '✅ Review agent validating itinerary...',
  ];

  const startLoadingProgress = () => {
    setLoadingStep(0);
    let step = 0;
    const interval = setInterval(() => {
      step += 1;
      if (step < LOADING_STEPS.length) {
        setLoadingStep(step);
      } else {
        clearInterval(interval);
      }
    }, 5000);
    return interval;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requestText.trim()) return;
    const interval = startLoadingProgress();
    const result = await submitPlan(requestText);
    clearInterval(interval);
    if (result) {
      setResponse(result);
      setView('result');
    }
  };

  const handleHealthCheck = async () => {
    setHealthStatus('Checking...');
    const health = await checkBackendHealth();
    if (health) {
      const remaining = (health as any).tokens?.remaining;
      const provider = (health as any).llm_provider ?? 'groq';
      const msg = remaining != null
        ? `✅ Backend online · ${provider.toUpperCase()} · ${remaining.toLocaleString()} tokens remaining`
        : `✅ Backend online · ${provider.toUpperCase()}`;
      setHealthStatus(msg);
    } else {
      setHealthStatus('❌ Backend offline or unreachable');
    }
    setTimeout(() => setHealthStatus(null), 5000);
  };

  const handleDestinationClick = (destination: string) => {
    const text = `Plan a 5-day trip to ${destination}. $2000 budget. Love food and sightseeing.`;
    setRequestText(text);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!bookingForm.name || !bookingForm.email) return;
    
    setBookingLoading(true);
    setBookingStatus(null);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/api/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...bookingForm,
          itinerary: response
        })
      });
      
      const data = await res.json();
      if (res.ok) {
        setBookingStatus({ type: 'success', message: data.message });
        setBookingForm({ name: '', email: '', comment: '' });
      } else {
        setBookingStatus({ type: 'error', message: data.detail || 'Failed to send booking request' });
      }
    } catch (err) {
      setBookingStatus({ type: 'error', message: 'Network error. Please try again later.' });
    } finally {
      setBookingLoading(false);
    }
  };

  // Home View
  if (view === 'home') {
    return (
      <div className="app">
        {/* Header */}
        <header className="header">
          <div className="header-content">
            <div className="logo">
              <GlobeIcon />
              <span>GlobeAI</span>
            </div>
            <nav className="nav-links">
              <a href="#" className="nav-link active">Explore</a>
              <a href="#" className="nav-link" onClick={(e) => { e.preventDefault(); alert('My Trips feature coming soon!'); }}>My Trips</a>
              <a href="#" className="nav-link" onClick={(e) => { e.preventDefault(); alert('Destinations explorer coming soon!'); }}>Destinations</a>
              <a href="#" className="nav-link" onClick={(e) => { e.preventDefault(); alert('Support center coming soon!'); }}>Support</a>
            </nav>
          <div className="header-actions">
              {healthStatus && (
                <span style={{ fontSize: '12px', color: healthStatus.startsWith('✅') ? '#16a34a' : '#dc2626', padding: '4px 8px', background: '#f9fafb', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
                  {healthStatus}
                </span>
              )}
              <button className="icon-button" onClick={handleHealthCheck} title="Check Backend Health">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                  <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
              </button>
            </div>
          </div>
        </header>

        {/* Error Display */}
        {error && (
          <div className="error-banner">
            <div className="error-content">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
            <button className="error-close" onClick={clearError}>×</button>
          </div>
        )}

        {/* Hero Section */}
        <section className="hero">
          <div className="hero-content">
            <h1>Your AI-Powered Travel Agent</h1>
            <p className="hero-subtitle">Tell me your dream trip and I'll build the perfect itinerary in seconds.</p>
            
            <form onSubmit={handleSubmit} className="search-box">
              <div className="search-input-wrapper">
                <span className="search-icon"><SearchIcon /></span>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Describe your perfect trip... (e.g., 5 days in NYC for art lovers on a budget)"
                  value={requestText}
                  onChange={(e) => setRequestText(e.target.value)}
                  disabled={loading}
                />
              </div>
              <button type="submit" className="search-button" disabled={loading || !requestText.trim()}>
                {loading ? (
                  <>
                    <span className="spinner" style={{ width: 16, height: 16, borderTopColor: '#333' }} />
                    Planning your trip...
                  </>
                ) : (
                  <>Generate Itinerary</>
                )}
              </button>
            </form>
            {loading && (
              <div style={{ marginTop: '16px', padding: '12px 16px', background: 'rgba(255,255,255,0.12)', borderRadius: '10px', backdropFilter: 'blur(8px)', color: '#fff', fontSize: '14px' }}>
                {LOADING_STEPS[loadingStep]}
              </div>
            )}
          </div>
        </section>

        {/* How It Works */}
        <section className="section">
          <h2 className="section-title">How GlobeAI Works</h2>
          <div className="property-grid">
            <div className="property-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '32px', background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)', textAlign: 'center', gap: '12px' }}>
              <div style={{ fontSize: '36px' }}>✍️</div>
              <div style={{ color: '#ffc107', fontWeight: 700, fontSize: '16px' }}>1. Describe Your Trip</div>
              <div style={{ color: '#9ca3af', fontSize: '13px' }}>Type your destination, duration, budget and preferences in plain English.</div>
            </div>
            <div className="property-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '32px', background: 'linear-gradient(135deg, #0f3460 0%, #16213e 100%)', textAlign: 'center', gap: '12px' }}>
              <div style={{ fontSize: '36px' }}>🤖</div>
              <div style={{ color: '#ffc107', fontWeight: 700, fontSize: '16px' }}>2. AI Agents Collaborate</div>
              <div style={{ color: '#9ca3af', fontSize: '13px' }}>Five specialized agents research destinations, plan logistics, and optimize your budget — in parallel.</div>
            </div>
          </div>
        </section>

        {/* Popular Destinations */}
        <section className="section">
          <h2 className="section-title">Popular Destinations</h2>
          <div className="destination-list">
            {POPULAR_DESTINATIONS.map((dest) => (
              <div key={dest.id} className="destination-card">
                <div className="destination-card-image-wrapper">
                  <img src={dest.image} alt={dest.name} className="destination-card-image" />
                  <button className="favorite-button">
                    <HeartIcon />
                  </button>
                </div>
                <div className="destination-card-content">
                  <div className="destination-header">
                    <h3 className="destination-name">{dest.name}</h3>
                    <div className="destination-rating">
                      <StarIcon />
                      <span>{dest.rating}</span>
                    </div>
                  </div>
                  <p className="destination-description">{dest.description}</p>
                  <div className="destination-footer">
                    <div className="destination-price">
                      <span className="price-label">Starting from</span>
                      <span className="price-value">${dest.price}<span className="price-unit">/trip</span></span>
                    </div>
                    <button 
                      className="view-trips-button"
                      onClick={() => handleDestinationClick(dest.name)}
                    >
                      View Trips
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Footer */}
        <footer className="footer">
          <div className="footer-content">
            <div className="footer-bottom">
              <div className="footer-logo">
                <GlobeIcon />
                <span>GlobeAI</span>
              </div>
              <p>© 2024 GlobeAI Travel. All rights reserved.</p>
            </div>
          </div>
        </footer>
      </div>
    );
  }

  // Result View
  if (!response) return null;

  const { final_itinerary, constraints, review_summary } = response;
  const { budget_rollup, neighborhoods, days, strategic_insight, budget_analysis, cost_optimization_tips } = final_itinerary;

  // ── helpers ──────────────────────────────────────────────────────────────
  const getCurrencySymbol = (currency: string): string => {
    const map: Record<string, string> = {
      INR: '₹', USD: '$', EUR: '€', GBP: '£', JPY: '¥',
      THB: '฿', SGD: 'S$', AUD: 'A$', CAD: 'C$', KRW: '₩', SEK: 'kr', NOK: 'kr',
    };
    return map[currency?.toUpperCase()] ?? currency ?? '$';
  };

  const currencySymbol = getCurrencySymbol(budget_rollup?.currency || constraints.currency);

  const formatAmount = (amount: number): string => {
    const sym = currencySymbol;
    if (amount >= 100000) return `${sym}${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000)   return `${sym}${(amount / 1000).toFixed(1)}k`;
    return `${sym}${Math.round(amount).toLocaleString()}`;
  };

  const allCities   = constraints.cities?.join(' & ') || constraints.destination_region;
  const primaryDest = constraints.cities?.[0] || constraints.destination_region;

  const heroSubtitle = constraints.preferences?.length
    ? `Curated for ${constraints.preferences.slice(0, 3).join(', ')} enthusiasts. Optimised for budget and transit efficiency.`
    : 'Your personalised AI-generated travel plan. Optimised for budget and transit efficiency.';

  const aboutText = `This ${constraints.duration_days}-day itinerary across ${constraints.destination_region} has been meticulously crafted by our AI agents to balance iconic sightseeing with authentic local experiences. We've optimised your travel routes to minimise transit time, giving you more hours to enjoy ${allCities}.`;

  const lodgingArea = (() => {
    if (days?.[0]?.lodging_area) return days[0].lodging_area;
    const firstCity = neighborhoods && Object.keys(neighborhoods)[0];
    return firstCity && (neighborhoods as Record<string, string[]>)[firstCity]?.[0]
      ? (neighborhoods as Record<string, string[]>)[firstCity][0]
      : `${primaryDest} City Centre`;
  })();

  const diningHighlight = (() => {
    const prefs = (constraints.preferences ?? []).map((p: string) => p.toLowerCase());
    if (prefs.some((p: string) => p.includes('michelin') || p.includes('fine dining'))) return 'Fine Dining';
    if (prefs.some((p: string) => p.includes('food') || p.includes('cuisine') || p.includes('local'))) return 'Local Cuisine';
    if (prefs.some((p: string) => p.includes('street'))) return 'Street Food';
    return 'Local Restaurants';
  })();

  // Merge duplicate categories (e.g., "stay" per city → one total)
  const groupedBudget = ((budget_rollup?.categories ?? []) as Array<{category: string; estimated_total: number}>).reduce<Record<string, number>>((acc, cat) => {
    acc[cat.category] = (acc[cat.category] ?? 0) + cat.estimated_total;
    return acc;
  }, {});

  const categoryLabels: Record<string, string> = {
    stay: 'Accommodation', food: 'Food & Dining', transport: 'Transport', activities: 'Activities',
  };



  return (
    <div className="app">
      {/* Yellow Header */}
      <header className="header" style={{ background: 'linear-gradient(135deg, #ffc107 0%, #e6ac00 100%)' }}>
        <div className="header-content">
          <div className="logo" style={{ color: '#1a1a1a' }}>
            <GlobeIcon />
            <span>GlobeAI</span>
          </div>
          <nav className="nav-links">
            <a href="#" className="nav-link" style={{ color: '#1a1a1a' }} onClick={() => setView('home')}>Explore</a>
            <a href="#" className="nav-link active" style={{ color: '#1a1a1a', borderBottomColor: '#1a1a1a' }}>Itineraries</a>
            <a href="#" className="nav-link" style={{ color: '#1a1a1a' }} onClick={(e) => { e.preventDefault(); alert('Destinations explorer coming soon!'); }}>Destinations</a>
            <a href="#" className="nav-link" style={{ color: '#1a1a1a' }} onClick={(e) => { e.preventDefault(); alert('Travel passes coming soon!'); }}>Passes</a>
            <a href="#" className="nav-link" style={{ color: '#1a1a1a' }} onClick={(e) => { e.preventDefault(); alert('Travel community coming soon!'); }}>Community</a>
          </nav>
          <div className="header-actions">
          </div>
        </div>
      </header>

      {/* Disclaimer Banner */}
      <div style={{ background: '#ffc107', padding: '8px', textAlign: 'center', fontSize: '13px' }}>
        <span>⚠️ Generated by AI. Verify all prices before booking.</span>
      </div>

      {/* Itinerary Result */}
      <div className="itinerary-page">
        {/* Hero */}
        <div className="itinerary-hero">
          <div className="itinerary-hero-content">
            <div className="itinerary-hero-badge">
              <AIAgentIcon />
              <span>AI Generated Itinerary</span>
            </div>
            <h1>Discover your perfect {constraints.duration_days}-day {allCities} itinerary</h1>
            <p className="itinerary-hero-subtitle">{heroSubtitle}</p>
          </div>
        </div>

        {/* Content */}
        <div className="itinerary-content">
          {/* Main Content */}
          <div className="itinerary-main">
            {/* About Section */}
            <div className="content-card">
              <h3 className="card-title">About Your {allCities} Journey</h3>
              <p className="about-text">{aboutText}</p>
              
              <div className="feature-grid">
                <div className="feature-card">
                  <div className="feature-icon"><BuildingIcon /></div>
                  <div className="feature-content">
                    <span className="feature-label">Stay</span>
                    <span className="feature-value">{lodgingArea}</span>
                  </div>
                </div>
                <div className="feature-card">
                  <div className="feature-icon"><UtensilsIcon /></div>
                  <div className="feature-content">
                    <span className="feature-label">Dining</span>
                    <span className="feature-value">{diningHighlight}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Strategy & Insights */}
            {(strategic_insight || budget_analysis || (final_itinerary as any).route_description) && (
              <div className="content-card" style={{ borderLeft: '4px solid #ffc107' }}>
                {(final_itinerary as any).route_description && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ margin: '0 0 8px', fontSize: '15px' }}>🗺️ Route Overview</h4>
                    <p style={{ margin: 0, fontSize: '14px', color: '#4b5563', lineHeight: 1.6 }}>{(final_itinerary as any).route_description}</p>
                  </div>
                )}
                {strategic_insight && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ margin: '0 0 8px', fontSize: '15px' }}>💡 Why This Itinerary Works</h4>
                    <p style={{ margin: 0, fontSize: '14px', color: '#4b5563', lineHeight: 1.6 }}>{strategic_insight}</p>
                  </div>
                )}
                {budget_analysis && (
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ margin: '0 0 8px', fontSize: '15px' }}>💰 Budget Reality Check</h4>
                    <p style={{ margin: 0, fontSize: '14px', color: '#4b5563', lineHeight: 1.6 }}>{budget_analysis}</p>
                  </div>
                )}
                {cost_optimization_tips && cost_optimization_tips.length > 0 && (
                  <div>
                    <h4 style={{ margin: '0 0 12px', fontSize: '15px' }}>🚀 Optimization Tips</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px' }}>
                      {cost_optimization_tips.map((tip: string, i: number) => (
                        <div key={i} style={{ background: '#f9fafb', padding: '10px', borderRadius: '8px', fontSize: '13px', color: '#4b5563', border: '1px solid #e5e7eb' }}>{tip}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Budget Breakdown */}
            <div className="content-card">
              <div className="budget-header">
                <h3 className="card-title" style={{ margin: 0 }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="5" width="20" height="14" rx="2"/>
                      <line x1="2" y1="10" x2="22" y2="10"/>
                    </svg>
                    Budget Breakdown
                  </span>
                </h3>
                <div className="budget-status" style={{ color: budget_rollup?.within_budget ? '#16a34a' : '#dc2626' }}>
                  {budget_rollup?.within_budget ? <CheckIcon /> : <span>⚠️</span>}
                  <span>{budget_rollup?.within_budget ? 'Within Budget' : 'Over Budget'}</span>
                </div>
              </div>
              
              <div className="budget-categories">
                {Object.entries(groupedBudget).map(([cat, total]) => (
                  <div key={cat} className="budget-category">
                    <div className="category-name">{categoryLabels[cat] || cat.charAt(0).toUpperCase() + cat.slice(1)}</div>
                    <div className="category-value">{formatAmount(total as number)}</div>
                  </div>
                ))}
              </div>
              <div className="budget-total">
                <span className="budget-total-label">Total Estimated Cost</span>
                <span className="budget-total-value">{formatAmount(budget_rollup?.grand_total ?? 0)}</span>
              </div>
              {(budget_rollup?.remaining_buffer ?? 0) > 0 && (
                <div style={{ marginTop: '8px', fontSize: '13px', color: '#16a34a' }}>
                  ✓ {formatAmount(budget_rollup.remaining_buffer)} remaining buffer
                </div>
              )}
            </div>

            {/* Daily Schedule */}
            <div className="content-card">
              <h3 className="card-title">Daily Schedule</h3>
              <div className="schedule-section">
                {(days as any[]).map((day: any) => (
                  <div key={day.day_number} className="day-card">
                    <div className="day-timeline">
                      <div className="day-timeline-dot" />
                    </div>
                    <div className="day-header">
                      <span className="day-badge">Day {day.day_number}</span>
                      <span className="day-title">{day.day_summary || `Explore ${day.city}`}</span>
                      {day.city && (
                        <span style={{ marginLeft: 'auto', fontSize: '12px', color: '#6b7280' }}>📍 {day.city}</span>
                      )}
                    </div>
                    <div className="activities-grid">
                      {((day as any).items as any[]).map((item: any, i: number) => (
                        <div key={i} className="activity-card">
                          <div className="activity-time">{item.time}</div>
                          <div className="activity-title">{item.activity_name}</div>
                          <div className="activity-description">{item.notes}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Agents */}
            <div className="content-card agents-section">
              <h3 className="card-title">Meet Your AI Agents</h3>
              <div className="agents-grid">
                <div className="agent-card">
                  <div className="agent-icon"><MapPinIcon /></div>
                  <div className="agent-name">Destination</div>
                  <div className="agent-role">Curated Attractions</div>
                  <div className="agent-status"><CheckIcon /> Verified</div>
                </div>
                <div className="agent-card">
                  <div className="agent-icon"><ClockIcon /></div>
                  <div className="agent-name">Logistics</div>
                  <div className="agent-role">Optimized Routing</div>
                  <div className="agent-status"><CheckIcon /> Verified</div>
                </div>
                <div className="agent-card">
                  <div className="agent-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="12" y1="1" x2="12" y2="23"/>
                      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                    </svg>
                  </div>
                  <div className="agent-name">Budget</div>
                  <div className="agent-role">Cost Optimization</div>
                  <div className="agent-status"><CheckIcon /> Verified</div>
                </div>
                <div className="agent-card">
                  <div className="agent-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                    </svg>
                  </div>
                  <div className="agent-name">Review</div>
                  <div className="agent-role">Quality Assurance</div>
                  <div className="agent-status"><CheckIcon /> PASS</div>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="itinerary-sidebar">
            <div className="sidebar-card">
              <div className="review-status-header">
                <span style={{ fontWeight: 600 }}>Review Status:</span>
                <div className="review-badge">
                  <CheckIcon />
                  <span>{review_summary.toUpperCase()}</span>
                </div>
              </div>
              
              <div className="trace-id">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                </svg>
                Trace ID: {traceId}
              </div>
              
              <div className="validated-by">Validated by 4 AI agents</div>
              
              <div style={{ marginTop: '20px', borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
                <div style={{ fontWeight: 600, marginBottom: '16px', fontSize: '16px', color: '#1a1a1a' }}>Book This Itinerary</div>
                
                {bookingStatus && (
                  <div style={{ 
                    padding: '12px', 
                    borderRadius: '8px', 
                    marginBottom: '16px', 
                    fontSize: '13px',
                    background: bookingStatus.type === 'success' ? '#f0fdf4' : '#fef2f2',
                    color: bookingStatus.type === 'success' ? '#166534' : '#991b1b',
                    border: `1px solid ${bookingStatus.type === 'success' ? '#bbf7d0' : '#fecaca'}`
                  }}>
                    {bookingStatus.message}
                  </div>
                )}

                <form onSubmit={handleBookingSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Full Name</label>
                    <input 
                      type="text" 
                      required
                      placeholder="John Doe"
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '14px' }}
                      value={bookingForm.name}
                      onChange={(e) => setBookingForm({ ...bookingForm, name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Email Address</label>
                    <input 
                      type="email" 
                      required
                      placeholder="john@example.com"
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '14px' }}
                      value={bookingForm.email}
                      onChange={(e) => setBookingForm({ ...bookingForm, email: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Comments / Special Requests</label>
                    <textarea 
                      placeholder="Tell us about any specific requirements..."
                      rows={3}
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '14px', resize: 'none' }}
                      value={bookingForm.comment}
                      onChange={(e) => setBookingForm({ ...bookingForm, comment: e.target.value })}
                    />
                  </div>
                  <button
                    type="submit"
                    className="book-button"
                    disabled={bookingLoading}
                    style={{ marginTop: '8px' }}
                  >
                    {bookingLoading ? 'Sending...' : 'Confirm Booking Request'} <ArrowRightIcon />
                  </button>
                </form>
              </div>
              
              <div style={{ marginTop: '20px', borderTop: '1px solid #e5e7eb', paddingTop: '16px' }}>
                <div style={{ fontWeight: 600, marginBottom: '12px', fontSize: '14px' }}>Trip Summary</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px', color: '#4b5563' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>📍 Destination</span>
                    <span style={{ fontWeight: 500, color: '#111' }}>{constraints.destination_region}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>📅 Duration</span>
                    <span style={{ fontWeight: 500, color: '#111' }}>{constraints.duration_days} days</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>🏙️ Cities</span>
                    <span style={{ fontWeight: 500, color: '#111', textAlign: 'right' }}>{constraints.cities?.join(', ')}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>💰 Budget</span>
                    <span style={{ fontWeight: 500, color: '#111' }}>{formatAmount(constraints.budget_total)}</span>
                  </div>
                  {(constraints.preferences?.length ?? 0) > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>❤️ Interests</span>
                      <span style={{ fontWeight: 500, color: '#111', textAlign: 'right', maxWidth: '120px' }}>{constraints.preferences.slice(0, 3).join(', ')}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="footer">
          <div className="footer-content">
            <div className="footer-bottom">
              <div className="footer-logo">
                <GlobeIcon />
                <span>GlobeAI</span>
              </div>
              <p>© 2024 GlobeAI Travel. All rights reserved.</p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
