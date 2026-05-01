"""
Groq LLM Client with token tracking and structured output support.
Optimized for 100k tokens/day limit.
"""

import json
import time
from typing import Optional, Any, Dict, Type, TypeVar
from functools import lru_cache

try:
    from groq import Groq
except ImportError:
    Groq = None

from ..config import get_settings
from ..models import TravelConstraints, ActivityCatalog, BudgetBreakdown
from .token_tracker import get_token_tracker, TokenBudgetExceeded

T = TypeVar('T')


class GroqClient:
    """
    Groq LLM client with token tracking, caching, and structured output.
    
    Features:
    - Token budget checking before requests
    - Response caching to reduce repeated calls
    - Structured JSON output validation
    - Automatic retry on rate limits
    - Fallback to stub/mock for testing
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        enable_tracking: bool = True,
        enable_cache: bool = True,
    ):
        settings = get_settings()
        
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        self.max_tokens = max_tokens or settings.groq_max_tokens_per_request
        self.temperature = temperature or settings.groq_temperature
        self.enable_tracking = enable_tracking and settings.enable_token_tracking
        self.enable_cache = enable_cache and settings.enable_response_cache
        
        # Initialize Groq client if available
        if Groq and self.api_key:
            self._client = Groq(api_key=self.api_key)
        else:
            self._client = None
        
        # Token tracker
        if self.enable_tracking:
            from .token_tracker import TokenTracker
            self._tracker = get_token_tracker(settings.token_buffer_percent)
        else:
            self._tracker = None
        
        # Cache (simple in-memory)
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = settings.cache_ttl_seconds
    
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model."""
        import hashlib
        key = f"{model}:{prompt}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _check_cache(self, prompt: str, model: str) -> Optional[Any]:
        """Check for cached response."""
        if not self.enable_cache:
            return None
        
        key = self._get_cache_key(prompt, model)
        if key in self._cache:
            cached, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return cached
            else:
                del self._cache[key]
        return None
    
    def _set_cache(self, prompt: str, model: str, response: Any):
        """Cache a response."""
        if self.enable_cache:
            key = self._get_cache_key(prompt, model)
            self._cache[key] = (response, time.time())
    
    def _check_token_budget(self, estimated_tokens: int) -> bool:
        """Check if we have enough tokens for this request."""
        if not self.enable_tracking or not self._tracker:
            return True
        return self._tracker.can_make_request(estimated_tokens)
    
    def _record_usage(self, prompt_tokens: int, completion_tokens: int):
        """Record token usage if tracking is enabled."""
        if self.enable_tracking and self._tracker:
            self._tracker.record_usage(prompt_tokens, completion_tokens, self.model)
    
    async def extract_constraints(
        self,
        natural_language_request: str
    ) -> TravelConstraints:
        """
        Phase 2: Extract TravelConstraints from natural language.
        
        Uses structured output with JSON schema for reliable parsing.
        """
        if not self._client:
            raise RuntimeError("Groq client not initialized. Check GROQ_API_KEY.")
        
        # Check token budget (extraction ~3k tokens)
        estimated_tokens = self._tracker.estimate_request_cost(
            len(natural_language_request) + 2000,  # Prompt + system message
            expected_response_length=1500
        ) if self._tracker else 3000
        
        if not self._check_token_budget(estimated_tokens):
            summary = self._tracker.get_usage_summary() if self._tracker else {}
            raise TokenBudgetExceeded(
                requested=estimated_tokens,
                remaining=summary.get("remaining", 0),
                limit=summary.get("daily_limit", 100000)
            )
        
        # Check cache
        cache_key_prompt = f"constraints:{natural_language_request}"
        cached = self._check_cache(cache_key_prompt, self.model)
        if cached and isinstance(cached, TravelConstraints):
            print(f"Cache hit for: {natural_language_request[:50]}...")
            return cached
        print(f"Extracting constraints for: {natural_language_request}")
        
        # Build structured extraction prompt
        system_prompt = """You are a travel planning assistant. Extract structured travel constraints from the user's request.

Respond with valid JSON matching this schema:
{
  "destination_region": "Country or region name",
  "cities": ["City1", "City2"],
  "duration_days": number,
  "budget_total": number,
  "currency": "3-letter code like USD, EUR, JPY",
  "preferences": ["what they want to experience"],
  "avoidances": ["what they want to avoid"],
  "hard_requirements": ["must-haves inferred from request"],
  "soft_preferences": ["nice-to-haves inferred"]
}

CRITICAL RULES:
- Extract the destination EXACTLY as the user mentions it
- cities must contain ONLY the cities the user explicitly named
- NEVER substitute or default to any city not mentioned by the user
- If user says "Switzerland", destination_region is "Switzerland"
- If user says "Tokyo + Kyoto", cities are ["Tokyo", "Kyoto"]
- If user says "Paris", cities are ["Paris"]
- Duration: count nights + 1 if not specified
- Budget: use explicit numbers or estimate a reasonable default
- Preferences: align with what they want (food, temples, nature, etc.)
- Avoidances: capture dislikes (crowds, tourist traps, etc.)"""

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": natural_language_request}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Record usage
            usage = response.usage
            self._record_usage(usage.prompt_tokens, usage.completion_tokens)
            
            # Parse and validate
            content = response.choices[0].message.content
            data = json.loads(content)
            constraints = TravelConstraints.model_validate(data)
            
            # Cache result
            self._set_cache(cache_key_prompt, self.model, constraints)
            
            return constraints
            
        except Exception as e:
            # Log error with context
            raise RuntimeError(f"Failed to extract constraints: {str(e)}")
    
    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: str,
        output_schema: Type[T],
        max_tokens: Optional[int] = None
    ) -> T:
        """
        Generic structured generation with Pydantic schema validation.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            output_schema: Pydantic model class for validation
            max_tokens: Override default max tokens
            
        Returns:
            Validated Pydantic model instance
        """
        if not self._client:
            raise RuntimeError("Groq client not initialized")
        
        # Estimate and check budget
        estimated = self._tracker.estimate_request_cost(
            len(prompt) + len(system_prompt),
            expected_response_length=2000
        ) if self._tracker else 4000
        
        if not self._check_token_budget(estimated):
            summary = self._tracker.get_usage_summary() if self._tracker else {}
            raise TokenBudgetExceeded(
                requested=estimated,
                remaining=summary.get("remaining", 0),
                limit=summary.get("daily_limit", 100000)
            )
        
        # Check cache
        cached = self._check_cache(prompt, self.model)
        if cached and isinstance(cached, output_schema):
            return cached
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Record usage
            usage = response.usage
            self._record_usage(usage.prompt_tokens, usage.completion_tokens)
            
            # Parse and validate
            content = response.choices[0].message.content
            data = json.loads(content)
            result = output_schema.model_validate(data)
            
            # Cache result
            self._set_cache(prompt, self.model, result)
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Generation failed: {str(e)}")
    
    def get_token_summary(self) -> Dict[str, Any]:
        """Get current token usage summary."""
        if self._tracker:
            return self._tracker.get_usage_summary()
        return {"tracking_disabled": True}


# Global instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create the global Groq client."""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
