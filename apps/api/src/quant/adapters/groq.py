"""
Groq adapter — LLM for news sentiment scoring and signal explanations.

Two models:
- llama-3.1-8b-instant    — fast, cheap, used for batch sentiment scoring
- llama-3.3-70b-versatile — used for per-signal plain-english explanations

Returns strict JSON for sentiment; free-form text for explanations.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from quant.adapters.base import HttpAdapter
from quant.adapters.exceptions import DataQualityError
from quant.config import settings

SentimentLabel = Literal["bearish", "neutral", "bullish"]

SENTIMENT_SYSTEM = (
    "You score financial news headlines for market impact on the listed tickers. "
    "Return ONLY minified JSON of the form "
    '{"score": <float in [-1,1]>, "label": "bearish"|"neutral"|"bullish", "rationale": "<1 sentence>"}. '
    "Do not include any prose outside the JSON."
)

EXPLANATION_SYSTEM = (
    "You are a quant analyst. Explain a model-generated trading signal in 3-4 sentences "
    "for an informed retail user. Reference the SHAP feature attributions provided. "
    "Never promise returns. Never use hype. Plain, specific, honest."
)

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class GroqAdapter(HttpAdapter):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    calls_per_minute = 30  # free tier safe; raise once confirmed

    def default_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.groq_api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        response_format: dict[str, str] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format is not None:
            payload["response_format"] = response_format
        data = await self.post_json("/chat/completions", json=payload)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as e:
            raise DataQualityError(f"[groq] malformed completion: {data!r}") from e

    # ------------------------------------------------------------
    # Sentiment
    # ------------------------------------------------------------
    async def score_sentiment(
        self, *, headline: str, summary: str | None, tickers: list[str]
    ) -> dict[str, Any]:
        user = (
            f"Tickers: {', '.join(tickers) if tickers else '(none specified)'}\n"
            f"Headline: {headline}\n"
            f"Summary: {summary or '(none)'}"
        )
        raw = await self._chat(
            model=settings.groq_model_fast,
            system=SENTIMENT_SYSTEM,
            user=user,
            temperature=0.0,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            m = _JSON_RE.search(raw)
            if not m:
                raise DataQualityError(f"[groq] non-JSON sentiment: {raw[:200]}") from None
            obj = json.loads(m.group(0))

        # clamp + normalize
        score = float(obj.get("score", 0.0))
        score = max(-1.0, min(1.0, score))
        label = obj.get("label", "neutral")
        if label not in ("bearish", "neutral", "bullish"):
            label = "neutral"
        return {
            "score": score,
            "label": label,
            "rationale": str(obj.get("rationale", ""))[:500],
            "model": settings.groq_model_fast,
        }

    # ------------------------------------------------------------
    # Signal explanation
    # ------------------------------------------------------------
    async def explain_signal(
        self,
        *,
        symbol: str,
        direction: str,
        confidence: float,
        horizon_days: int,
        top_shap: list[tuple[str, float]],
        recent_news_sentiment: float | None = None,
    ) -> str:
        shap_lines = "\n".join(f"  - {name}: {value:+.4f}" for name, value in top_shap[:8])
        user = (
            f"Symbol: {symbol}\n"
            f"Direction: {direction}  |  Confidence: {confidence:.2%}  |  "
            f"Horizon: {horizon_days} trading days\n"
            f"Top SHAP feature attributions (positive = supports BUY):\n{shap_lines}\n"
            + (
                f"Recent news sentiment (rolling 1d mean): {recent_news_sentiment:+.2f}\n"
                if recent_news_sentiment is not None
                else ""
            )
        )
        return (await self._chat(
            model=settings.groq_model_smart,
            system=EXPLANATION_SYSTEM,
            user=user,
            temperature=0.3,
            max_tokens=350,
        )).strip()
