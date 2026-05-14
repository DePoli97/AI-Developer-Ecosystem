"""
Token cost estimator — unified interface across Anthropic, OpenAI, and Google.

Why this exists:
    Every production LLM system needs to track token usage and cost. Each
    provider has a different pricing structure, different unit (tokens vs
    characters), and different SDK response shapes. This module normalises
    all of that behind a single `estimate_cost()` call that takes a raw API
    response (or explicit token counts) and returns a structured
    `CostEstimate` with input, output, and total cost in USD.

Supported providers:
    - Anthropic  (claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5, …)
    - OpenAI     (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, …)
    - Google     (gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash, …)

No external dependencies required beyond what you already have.
Prices are embedded as constants — update them when providers reprice.

Public API:
    estimate_cost(response, *, provider)  -> CostEstimate
    estimate_from_tokens(model, input_tokens, output_tokens)  -> CostEstimate
    CostEstimate.total_usd                -> float
    CostEstimate.as_dict()                -> dict
    PRICE_TABLE                           -> dict[str, ModelPricing]

Run the file directly for a self-test:
    python token_cost_estimator.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any


# ── Pricing table ─────────────────────────────────────────────────────────────
# Prices are per 1 000 000 tokens (per-million) in USD.
# Last updated: 2026-05.  Check provider dashboards for current prices.

@dataclass(frozen=True)
class ModelPricing:
    provider: str
    model: str
    input_per_million: float
    output_per_million: float
    # Some models have a cheaper cached-input price (e.g. Anthropic prompt cache)
    cached_input_per_million: float | None = None

    def cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> tuple[float, float]:
        """Return (input_cost_usd, output_cost_usd)."""
        non_cached = input_tokens - cached_input_tokens
        input_cost = non_cached * self.input_per_million / 1_000_000
        if cached_input_tokens and self.cached_input_per_million is not None:
            input_cost += cached_input_tokens * self.cached_input_per_million / 1_000_000
        output_cost = output_tokens * self.output_per_million / 1_000_000
        return input_cost, output_cost


PRICE_TABLE: dict[str, ModelPricing] = {
    # ── Anthropic ──────────────────────────────────────────────────────────────
    "claude-opus-4-6":         ModelPricing("anthropic", "claude-opus-4-6",         15.00, 75.00, 1.50),
    "claude-sonnet-4-6":       ModelPricing("anthropic", "claude-sonnet-4-6",        3.00, 15.00, 0.30),
    "claude-haiku-4-5":        ModelPricing("anthropic", "claude-haiku-4-5",         0.80,  4.00, 0.08),
    # Legacy
    "claude-3-opus-20240229":  ModelPricing("anthropic", "claude-3-opus-20240229",  15.00, 75.00, 1.50),
    "claude-3-5-sonnet-20241022": ModelPricing("anthropic", "claude-3-5-sonnet-20241022", 3.00, 15.00, 0.30),
    "claude-3-haiku-20240307": ModelPricing("anthropic", "claude-3-haiku-20240307",  0.25,  1.25, 0.03),

    # ── OpenAI ────────────────────────────────────────────────────────────────
    "gpt-4o":                  ModelPricing("openai", "gpt-4o",               2.50, 10.00, 1.25),
    "gpt-4o-mini":             ModelPricing("openai", "gpt-4o-mini",          0.15,  0.60, 0.075),
    "gpt-4-turbo":             ModelPricing("openai", "gpt-4-turbo",         10.00, 30.00),
    "gpt-4":                   ModelPricing("openai", "gpt-4",               30.00, 60.00),
    "gpt-3.5-turbo":           ModelPricing("openai", "gpt-3.5-turbo",        0.50,  1.50),
    "o1":                      ModelPricing("openai", "o1",                  15.00, 60.00, 7.50),
    "o1-mini":                 ModelPricing("openai", "o1-mini",              3.00, 12.00, 1.50),
    "o3-mini":                 ModelPricing("openai", "o3-mini",              1.10,  4.40, 0.55),

    # ── Google ────────────────────────────────────────────────────────────────
    "gemini-1.5-pro":          ModelPricing("google", "gemini-1.5-pro",       3.50, 10.50),
    "gemini-1.5-flash":        ModelPricing("google", "gemini-1.5-flash",     0.075, 0.30),
    "gemini-2.0-flash":        ModelPricing("google", "gemini-2.0-flash",     0.10,  0.40),
    "gemini-2.0-flash-lite":   ModelPricing("google", "gemini-2.0-flash-lite",0.075, 0.30),
}


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class CostEstimate:
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    input_cost_usd: float = field(init=False)
    output_cost_usd: float = field(init=False)
    total_usd: float = field(init=False)
    _pricing: ModelPricing | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self._pricing is not None:
            self.input_cost_usd, self.output_cost_usd = self._pricing.cost(
                self.input_tokens, self.output_tokens, self.cached_input_tokens
            )
        else:
            self.input_cost_usd = 0.0
            self.output_cost_usd = 0.0
        self.total_usd = round(self.input_cost_usd + self.output_cost_usd, 8)

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "provider": self.provider,
            "tokens": {
                "input": self.input_tokens,
                "output": self.output_tokens,
                "cached_input": self.cached_input_tokens,
            },
            "cost_usd": {
                "input": round(self.input_cost_usd, 8),
                "output": round(self.output_cost_usd, 8),
                "total": self.total_usd,
            },
        }

    def __str__(self) -> str:
        return (
            f"{self.model} | "
            f"in={self.input_tokens:,} out={self.output_tokens:,} tok | "
            f"${self.total_usd:.6f}"
        )


# ── Public functions ──────────────────────────────────────────────────────────

def estimate_from_tokens(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> CostEstimate:
    """
    Build a CostEstimate directly from token counts.

    Parameters
    ----------
    model:
        Model string exactly as used in the API, e.g. ``"gpt-4o"``.
    input_tokens, output_tokens:
        Raw token counts from usage objects.
    cached_input_tokens:
        Tokens served from the provider's prompt cache (if applicable).
    """
    pricing = _lookup_pricing(model)
    provider = pricing.provider if pricing else _guess_provider(model)
    return CostEstimate(
        model=model,
        provider=provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        _pricing=pricing,
    )


def estimate_cost(response: Any, *, provider: str | None = None) -> CostEstimate:
    """
    Extract token counts from a raw API response object and return a CostEstimate.

    Supports:
    - anthropic.types.Message
    - openai.types.chat.ChatCompletion
    - google.generativeai GenerateContentResponse / types.GenerateContentResponse
    - Any object with a .usage attribute that has input_tokens/output_tokens or
      prompt_tokens/completion_tokens fields.

    Parameters
    ----------
    response:
        The raw response object returned by the provider SDK.
    provider:
        Optional hint: "anthropic", "openai", or "google".
        If omitted, the function tries to infer the provider from the response type.
    """
    provider = provider or _detect_provider(response)

    if provider == "anthropic":
        return _from_anthropic(response)
    if provider == "openai":
        return _from_openai(response)
    if provider == "google":
        return _from_google(response)

    # Generic fallback: try common usage shapes
    return _from_generic(response)


# ── Provider-specific parsers ─────────────────────────────────────────────────

def _from_anthropic(response: Any) -> CostEstimate:
    model = getattr(response, "model", "unknown")
    usage = getattr(response, "usage", None)
    if usage is None:
        raise ValueError("Response has no .usage attribute")
    input_tokens = getattr(usage, "input_tokens", 0)
    output_tokens = getattr(usage, "output_tokens", 0)
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return estimate_from_tokens(model, input_tokens, output_tokens, cache_read)


def _from_openai(response: Any) -> CostEstimate:
    model = getattr(response, "model", "unknown")
    usage = getattr(response, "usage", None)
    if usage is None:
        raise ValueError("Response has no .usage attribute")
    input_tokens = getattr(usage, "prompt_tokens", 0)
    output_tokens = getattr(usage, "completion_tokens", 0)
    # OpenAI cached tokens live in usage.prompt_tokens_details.cached_tokens
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details:
        cached = getattr(details, "cached_tokens", 0) or 0
    return estimate_from_tokens(model, input_tokens, output_tokens, cached)


def _from_google(response: Any) -> CostEstimate:
    # Google Generative AI SDK shape varies; handle both old and new
    metadata = getattr(response, "usage_metadata", None) or getattr(response, "usage", None)
    if metadata is None:
        raise ValueError("Response has no usage_metadata / usage attribute")
    input_tokens = (
        getattr(metadata, "prompt_token_count", None)
        or getattr(metadata, "input_tokens", 0)
    )
    output_tokens = (
        getattr(metadata, "candidates_token_count", None)
        or getattr(metadata, "output_tokens", 0)
    )
    # Model name: response.model or response.model_version
    model = (
        getattr(response, "model", None)
        or getattr(response, "model_version", "gemini-1.5-pro")
    )
    # Google uses "models/gemini-1.5-pro" format — strip prefix
    if isinstance(model, str) and "/" in model:
        model = model.split("/")[-1]
    return estimate_from_tokens(model, input_tokens or 0, output_tokens or 0)


def _from_generic(response: Any) -> CostEstimate:
    usage = getattr(response, "usage", None)
    if usage is None:
        raise ValueError("Cannot extract usage from response: no .usage attribute found.")
    # Try Anthropic shape first, then OpenAI shape
    input_tokens = (
        getattr(usage, "input_tokens", None)
        or getattr(usage, "prompt_tokens", 0)
    )
    output_tokens = (
        getattr(usage, "output_tokens", None)
        or getattr(usage, "completion_tokens", 0)
    )
    model = getattr(response, "model", "unknown")
    return estimate_from_tokens(model, input_tokens or 0, output_tokens or 0)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lookup_pricing(model: str) -> ModelPricing | None:
    if model in PRICE_TABLE:
        return PRICE_TABLE[model]
    # Partial match: find a key that is a prefix of the given model string
    for key, pricing in PRICE_TABLE.items():
        if model.startswith(key) or key.startswith(model):
            return pricing
    return None


def _guess_provider(model: str) -> str:
    if "claude" in model:
        return "anthropic"
    if model.startswith(("gpt-", "o1", "o3", "text-")):
        return "openai"
    if "gemini" in model or "palm" in model:
        return "google"
    return "unknown"


def _detect_provider(response: Any) -> str:
    type_name = type(response).__module__ + "." + type(response).__qualname__
    if "anthropic" in type_name:
        return "anthropic"
    if "openai" in type_name:
        return "openai"
    if "google" in type_name or "generativeai" in type_name:
        return "google"
    # Fallback: inspect the model field
    model = getattr(response, "model", "") or ""
    return _guess_provider(str(model))


# ── Self-test ─────────────────────────────────────────────────────────────────

def _run_tests() -> None:
    import traceback

    failures: list[str] = []

    def check(name: str, condition: bool, msg: str = "") -> None:
        if not condition:
            failures.append(f"FAIL [{name}]: {msg}")
            print(f"  FAIL  {name}: {msg}")
        else:
            print(f"  ok    {name}")

    print("Running token_cost_estimator self-tests...\n")

    # Basic estimate
    est = estimate_from_tokens("claude-sonnet-4-6", input_tokens=1_000, output_tokens=500)
    check("sonnet input cost",  abs(est.input_cost_usd  - 0.003)   < 1e-7, str(est.input_cost_usd))
    check("sonnet output cost", abs(est.output_cost_usd - 0.0075)  < 1e-7, str(est.output_cost_usd))
    check("sonnet total",       abs(est.total_usd       - 0.0105)  < 1e-6, str(est.total_usd))

    # Cached tokens
    est_cached = estimate_from_tokens("claude-sonnet-4-6", 1_000, 500, cached_input_tokens=800)
    check("cached cheaper than non-cached", est_cached.total_usd < est.total_usd, "")

    # OpenAI
    est_oai = estimate_from_tokens("gpt-4o", 2_000, 800)
    check("gpt-4o provider", est_oai.provider == "openai", est_oai.provider)
    check("gpt-4o total > 0", est_oai.total_usd > 0, str(est_oai.total_usd))

    # Google
    est_goog = estimate_from_tokens("gemini-1.5-flash", 10_000, 2_000)
    check("gemini provider", est_goog.provider == "google", est_goog.provider)
    check("gemini total > 0", est_goog.total_usd > 0, str(est_goog.total_usd))

    # Unknown model — should not raise, just return 0 cost
    est_unk = estimate_from_tokens("llama-future-3", 500, 200)
    check("unknown model no exception", est_unk.total_usd == 0.0, str(est_unk.total_usd))
    check("unknown model provider guess", est_unk.provider == "unknown", est_unk.provider)

    # as_dict() shape
    d = est.as_dict()
    check("as_dict keys", set(d) == {"model", "provider", "tokens", "cost_usd"}, str(set(d)))
    check("as_dict nested tokens", "input" in d["tokens"], str(d))

    # Comparison across models
    print("\nCost comparison — 10k input, 2k output:")
    for model in ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-6",
                  "gpt-4o-mini", "gpt-4o", "gemini-2.0-flash", "gemini-1.5-pro"]:
        e = estimate_from_tokens(model, 10_000, 2_000)
        print(f"  {e}")

    if failures:
        print(f"\n{len(failures)} test(s) failed:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("\nAll tests passed.")


if __name__ == "__main__":
    _run_tests()
