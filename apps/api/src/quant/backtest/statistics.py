"""
Selection-bias-aware performance statistics.

Deflated Sharpe Ratio (DSR) — Bailey & López de Prado (2014), "The Deflated
Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and
Non-Normality". When you try N strategies and pick the best, the best's Sharpe
is upward-biased. DSR adjusts for:
    - number of trials N
    - skewness and kurtosis of returns
    - variance of the sampled Sharpes
and produces a probability that the observed Sharpe is > 0 after deflation.

PBO — "The Probability of Backtest Overfitting" (López de Prado 2016), via
Combinatorially Symmetric Cross-Validation (CSCV). Partition the backtest
returns matrix (T x N, T periods by N strategies) into S contiguous sub-slices,
for every combination C(S, S/2) of in-sample slices compute the best strategy
IS and its OOS rank; the fraction of trials where the IS-best underperforms the
OOS median is PBO.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any

import numpy as np

EULER_MASCHERONI = 0.5772156649015329


def sharpe_ratio(returns: np.ndarray, periods_per_year: int = 252) -> float:
    """Annualized Sharpe. Assumes rf = 0; subtract explicitly if you need it."""
    if returns.size < 2:
        return float("nan")
    mu = returns.mean()
    sd = returns.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(mu / sd * math.sqrt(periods_per_year))


def _expected_max_sharpe(n_trials: int) -> float:
    """
    Expected value of the max of N iid standard normals. Uses Bailey & López
    de Prado's approximation: E[max_N] ≈ (1-γ) Φ^-1(1-1/N) + γ Φ^-1(1-1/(Ne)).
    """
    if n_trials < 2:
        return 0.0
    from scipy.stats import norm

    g = EULER_MASCHERONI
    a = norm.ppf(1.0 - 1.0 / n_trials)
    b = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return float((1 - g) * a + g * b)


def deflated_sharpe_ratio(
    observed_sharpe: float,
    *,
    n_trials: int,
    sharpes_std: float,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """
    Probability that the true Sharpe > 0, given that we picked the best of
    `n_trials` strategies and observed `observed_sharpe` over `n_obs` periods.

    Args:
        observed_sharpe: annualized Sharpe of the selected strategy.
        n_trials: number of strategies tried (the selection pool).
        sharpes_std: std of the Sharpe estimates across the trials.
        n_obs: number of return observations for the selected strategy.
        skew: skewness of returns (use 0 if unknown — most conservative).
        kurtosis: kurtosis of returns (3 = normal).

    Returns:
        P(SR* > 0 | selection bias, non-normality). Values > 0.95 are strong.
    """
    from scipy.stats import norm

    sr0 = sharpes_std * _expected_max_sharpe(n_trials)
    # Non-normality-adjusted estimator variance.
    num = observed_sharpe - sr0
    denom = math.sqrt((1 - skew * observed_sharpe + (kurtosis - 1) / 4.0 * observed_sharpe**2) / (n_obs - 1))
    if denom == 0:
        return float("nan")
    return float(norm.cdf(num / denom))


def probability_of_backtest_overfitting(returns_matrix: np.ndarray, n_slices: int = 16) -> dict[str, Any]:
    """
    CSCV-based PBO. `returns_matrix` is (T, N) — T time steps × N strategies.

    Returns {"pbo": float, "logits": list[float], "n_trials": int}.
    PBO ∈ [0, 1]. PBO > 0.5 means the in-sample winner is more likely than
    not to be a below-median performer out of sample — i.e. the pipeline is
    overfitting its selection.
    """
    if returns_matrix.ndim != 2:
        raise ValueError("returns_matrix must be 2-D (T × N)")
    t, n = returns_matrix.shape
    if n_slices % 2 != 0:
        raise ValueError("n_slices must be even")
    if n_slices > t:
        raise ValueError(f"n_slices={n_slices} > T={t}")

    # Equal-size contiguous slices.
    edges = np.linspace(0, t, n_slices + 1, dtype=int)
    slices = [returns_matrix[edges[i] : edges[i + 1]] for i in range(n_slices)]

    half = n_slices // 2
    logits: list[float] = []
    for is_idx in combinations(range(n_slices), half):
        oos_idx = [i for i in range(n_slices) if i not in is_idx]
        is_rets = np.concatenate([slices[i] for i in is_idx], axis=0)
        oos_rets = np.concatenate([slices[i] for i in oos_idx], axis=0)

        # Sharpe-like: mean / std for each strategy, over the IS and OOS slices.
        is_sr = _col_sharpe(is_rets)
        oos_sr = _col_sharpe(oos_rets)

        best_is = int(np.argmax(is_sr))
        # Rank of the IS-best strategy in OOS (0 = worst, n-1 = best).
        rank = float((oos_sr.argsort().argsort())[best_is])
        # Normalize to (0, 1) and convert to logit.
        w = (rank + 1) / (n + 1)
        w = min(max(w, 1e-6), 1 - 1e-6)
        logits.append(math.log(w / (1 - w)))

    pbo = float(sum(1 for lg in logits if lg < 0) / len(logits))
    return {"pbo": pbo, "logits": logits, "n_trials": len(logits)}


def _col_sharpe(mat: np.ndarray) -> np.ndarray:
    mu = mat.mean(axis=0)
    sd = mat.std(axis=0, ddof=1)
    sd = np.where(sd == 0, np.nan, sd)
    return mu / sd
