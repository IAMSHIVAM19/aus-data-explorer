"""
Statistical Forecasting Engine (Holt-Winters Triple Exponential Smoothing)
Aus Gov Data Explorer - Addition 2

Why Holt-Winters instead of ARIMA?
1. Interpretability: Decomposes series explicitly into baseline level, velocity (trend),
   and 12-month calendar seasonality.
2. Determinism & Stability: Unlike ARIMA, which requires iterative numerical search
   for autoregressive/moving-average lag polynomials (p, d, q) that can diverge or fail
   to invert on macroeconomic shock discontinuities (like COVID-19 in 2020), Holt-Winters
   guarantees a stable, closed-form recursive solution.
3. Educational Clarity: Clear mathematical recurrence relations that can be understood
   and explained in LEARNING_NOTES.md without a black-box optimizer.
"""

from typing import List, Dict, Any, Tuple
import math
from datetime import datetime


def add_months(orig_date_str: str, n_months: int) -> str:
    """Safely increments a YYYY-MM-DD date string by n months."""
    dt = datetime.strptime(orig_date_str, "%Y-%m-%d")
    month = dt.month - 1 + n_months
    year = dt.year + month // 12
    month = month % 12 + 1
    return f"{year:04d}-{month:02d}-01"


def fit_holt_winters(
    series: List[float],
    season_length: int = 12,
    alpha: float = 0.3,
    beta: float = 0.05,
    gamma: float = 0.15
) -> Tuple[float, float, List[float], float]:
    """
    Fits additive Holt-Winters exponential smoothing across historical observations.
    
    Equations:
    - Level:   l_t = alpha * (y_t - s_{t-m}) + (1 - alpha) * (l_{t-1} + b_{t-1})
    - Trend:   b_t = beta  * (l_t - l_{t-1})  + (1 - beta)  * b_{t-1}
    - Season:  s_t = gamma * (y_t - l_t)      + (1 - gamma) * s_{t-m}
    
    Returns: (final_level, final_trend, final_seasonal_factors, residual_variance)
    """
    n = len(series)
    m = season_length
    if n < 2 * m:
        # Fallback to simple linear Holt's if series is shorter than 2 seasons
        m = max(1, n // 2)

    # 1. Initialize level and trend from first season averages
    season1_avg = sum(series[:m]) / m
    season2_avg = sum(series[m:2*m]) / m if n >= 2*m else season1_avg
    initial_trend = (season2_avg - season1_avg) / m
    initial_level = season1_avg

    # 2. Initialize seasonal components
    seasonals = [series[i] - initial_level for i in range(m)]

    # 3. Recursive state updates & residual tracking
    level = initial_level
    trend = initial_trend
    fitted_values = []
    residuals = []

    for i in range(n):
        y_t = series[i]
        s_idx = i % m
        prev_s = seasonals[s_idx]

        # One-step-ahead point forecast
        y_hat = level + trend + prev_s
        fitted_values.append(y_hat)
        residuals.append(y_t - y_hat)

        # Update level, trend, season
        last_level = level
        level = alpha * (y_t - prev_s) + (1.0 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1.0 - beta) * trend
        seasonals[s_idx] = gamma * (y_t - level) + (1.0 - gamma) * prev_s

    # Compute residual variance (sigma^2)
    res_var = sum(r**2 for r in residuals) / max(1, len(residuals))
    return level, trend, seasonals, res_var


def generate_statistical_forecast(
    historical_rows: List[Dict[str, Any]],
    date_col: str = "date",
    val_col: str = "value",
    horizon_months: int = 12,
    metric_label: str = "Unemployment Rate"
) -> Dict[str, Any]:
    """
    Generates a 12-month forward statistical projection with 80% and 95% confidence intervals.
    
    Confidence Interval Derivation:
    In Holt-Winters additive models, uncertainty compounds with the forecast horizon h:
        Var(y_{t+h}) = sigma^2 * (1 + sum_{j=1}^{h-1} c_j^2)
        where c_j = 1 + j * beta
    
    Confidence Multipliers (Standard Normal Distribution z-scores):
    - 80% CI: z = 1.282 (10% excluded in each tail)
    - 95% CI: z = 1.960 (2.5% excluded in each tail)
    """
    if len(historical_rows) < 12:
        raise ValueError("Insufficient historical observations to fit seasonal forecasting model (minimum 12 required).")

    # Sort historical rows chronologically
    sorted_hist = sorted(historical_rows, key=lambda r: str(r[date_col]))
    values = [float(r[val_col]) for r in sorted_hist if r.get(val_col) is not None]
    dates = [str(r[date_col]) for r in sorted_hist if r.get(val_col) is not None]

    # Fit Holt-Winters model
    level, trend, seasonals, res_var = fit_holt_winters(values, season_length=12)
    sigma = math.sqrt(max(0.0001, res_var))

    # Generate forward projections
    last_date = dates[-1]
    m = len(seasonals)
    n_hist = len(values)

    projected_points = []
    compound_variance_factor = 1.0

    for h in range(1, horizon_months + 1):
        target_date = add_months(last_date, h)
        s_idx = (n_hist + h - 1) % m
        seasonal_comp = seasonals[s_idx]

        # Mean point estimate
        y_hat = round(level + (h * trend) + seasonal_comp, 2)
        # Ensure macroeconomic rates (e.g. unemployment) cannot be negative
        y_hat = max(0.1, y_hat)

        # Standard error increases with horizon
        compound_variance_factor += (1.0 + h * 0.05) ** 2
        se_h = sigma * math.sqrt(compound_variance_factor)

        # Confidence bounds: 80% (z=1.282), 95% (z=1.960)
        ci_80_lower = max(0.0, round(y_hat - 1.282 * se_h, 2))
        ci_80_upper = round(y_hat + 1.282 * se_h, 2)
        ci_95_lower = max(0.0, round(y_hat - 1.960 * se_h, 2))
        ci_95_upper = round(y_hat + 1.960 * se_h, 2)

        projected_points.append({
            date_col: target_date,
            "projected_mean": y_hat,
            "ci_80_lower": ci_80_lower,
            "ci_80_upper": ci_80_upper,
            "ci_95_lower": ci_95_lower,
            "ci_95_upper": ci_95_upper,
            "is_projected": True
        })

    # Historical context: take last 24 observations for smooth visual transition
    recent_history = []
    for r in sorted_hist[-24:]:
        recent_history.append({
            date_col: r[date_col],
            "historical_value": float(r[val_col]),
            "projected_mean": None,
            "ci_80_lower": None,
            "ci_80_upper": None,
            "ci_95_lower": None,
            "ci_95_upper": None,
            "is_projected": False
        })

    # Stitch the last historical point with the first projected point for visual continuity
    if recent_history:
        recent_history[-1]["projected_mean"] = recent_history[-1]["historical_value"]

    combined_chart_data = recent_history + projected_points

    return {
        "is_forecast": True,
        "caption": "Statistical projection, not an official forecast.",
        "method": "Holt-Winters Triple Exponential Smoothing (m=12, Additive)",
        "horizon_months": horizon_months,
        "metric_label": metric_label,
        "last_observed_date": last_date,
        "last_observed_value": values[-1],
        "projected_final_date": projected_points[-1][date_col],
        "projected_final_mean": projected_points[-1]["projected_mean"],
        "projected_points": projected_points,
        "chart_data": combined_chart_data
    }
