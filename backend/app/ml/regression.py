"""Machine-learning layer (pure functions, no DB/HTTP).

Multiple Linear Regression:
    energy_consumed_wh = intercept + b1*hours_used + b2*age_years + b3*power_rating_watts
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

FEATURES = ["hours_used", "age_years", "power_rating_watts"]
TARGET = "energy_consumed_wh"
FEATURE_LABELS = {
    "hours_used": "Hours used",
    "age_years": "Appliance age",
    "power_rating_watts": "Power rating",
}
COEF_KEYS = {
    "hours_used": "coefficient_hours",
    "age_years": "coefficient_age",
    "power_rating_watts": "coefficient_watts",
}
MIN_TRAINING_ROWS = 10
PROFILE_WINDOW_DAYS = 28  # recent window used to learn weekday usage habits
SCATTER_SAMPLE = 600


class InsufficientDataError(ValueError):
    """Raised when there is not enough usage history to fit a model."""


@dataclass
class TrainResult:
    params: dict[str, float]
    diagnostics: dict[str, Any]


def to_frame(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(list(rows))
    if df.empty:
        return df
    for col in FEATURES + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="raise").astype(float)
    df["date"] = pd.to_datetime(df["date"])
    return df


def train(rows: Iterable[dict[str, Any]]) -> TrainResult:
    df = to_frame(rows)
    if len(df) < MIN_TRAINING_ROWS:
        raise InsufficientDataError(
            f"Need at least {MIN_TRAINING_ROWS} usage logs to train; found {len(df)}."
        )
    X = df[FEATURES].to_numpy()
    y = df[TARGET].to_numpy()
    model = LinearRegression().fit(X, y)
    y_hat = model.predict(X)

    params = {COEF_KEYS[f]: float(c) for f, c in zip(FEATURES, model.coef_)}
    params["intercept"] = float(model.intercept_)
    params["r_squared"] = float(r2_score(y, y_hat))
    return TrainResult(params=params, diagnostics=diagnostics(df, params))


def predict_wh(params: dict[str, float], hours: np.ndarray | float, age: np.ndarray | float,
               watts: np.ndarray | float) -> np.ndarray:
    """Apply stored coefficients. Zero hours => zero energy; negatives clipped to 0."""
    hours = np.asarray(hours, dtype=float)
    raw = (params["intercept"]
           + params["coefficient_hours"] * hours
           + params["coefficient_age"] * np.asarray(age, dtype=float)
           + params["coefficient_watts"] * np.asarray(watts, dtype=float))
    return np.where(hours > 0, np.clip(raw, 0, None), 0.0)


def diagnostics(df: pd.DataFrame, params: dict[str, float]) -> dict[str, Any]:
    """Accuracy metrics, factor importance and actual-vs-predicted points for charts."""
    y = df[TARGET].to_numpy()
    raw_pred = (params["intercept"]
                + sum(params[COEF_KEYS[f]] * df[f].to_numpy() for f in FEATURES))
    stds = df[FEATURES].std(ddof=0)
    means = df[FEATURES].mean()

    # Standardised effect = how many Wh the prediction moves for a 1-std change in the factor.
    effects = {f: abs(params[COEF_KEYS[f]]) * float(stds[f]) for f in FEATURES}
    total_effect = sum(effects.values()) or 1.0
    factors = sorted(
        (
            {
                "feature": f,
                "label": FEATURE_LABELS[f],
                "coefficient": params[COEF_KEYS[f]],
                "std": float(stds[f]),
                "mean": float(means[f]),
                "standardized_effect_wh": effects[f],
                "share": effects[f] / total_effect,
            }
            for f in FEATURES
        ),
        key=lambda d: d["standardized_effect_wh"],
        reverse=True,
    )

    sample = df.assign(predicted=raw_pred)
    if len(sample) > SCATTER_SAMPLE:
        sample = sample.sample(SCATTER_SAMPLE, random_state=42)
    points = [
        {
            "actual_wh": round(float(r[TARGET]), 1),
            "predicted_wh": round(float(r["predicted"]), 1),
            "appliance_name": r["appliance_name"],
            "category": r["category"],
            "hours_used": float(r["hours_used"]),
        }
        for _, r in sample.iterrows()
    ]

    return {
        "n_samples": int(len(df)),
        "date_from": df["date"].min().date().isoformat(),
        "date_to": df["date"].max().date().isoformat(),
        "mae_wh": float(mean_absolute_error(y, raw_pred)),
        "rmse_wh": float(np.sqrt(mean_squared_error(y, raw_pred))),
        "mean_actual_wh": float(y.mean()),
        "factors": factors,
        "top_driver": factors[0]["feature"],
        "points": points,
    }


def weekday_profiles(rows: Iterable[dict[str, Any]], appliances: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Mean hours per weekday (Mon=0..Sun=6) per appliance over the recent window.

    Days without a log in the window count as 0 hours (appliance not used).
    """
    df = to_frame(rows)
    profiles: dict[str, list[float]] = {str(a["id"]): [0.0] * 7 for a in appliances}
    if df.empty:
        return profiles
    end = df["date"].max()
    start = end - pd.Timedelta(days=PROFILE_WINDOW_DAYS - 1)
    recent = df[df["date"] >= start].copy()
    recent["weekday"] = recent["date"].dt.weekday
    calendar = pd.date_range(start, end, freq="D")
    days_per_weekday = pd.Series(calendar.weekday).value_counts().to_dict()

    sums = recent.groupby([recent["appliance_id"].astype(str), "weekday"])["hours_used"].sum()
    for (aid, wd), total in sums.items():
        if aid in profiles:
            profiles[aid][int(wd)] = float(total) / days_per_weekday.get(int(wd), 1)
    return profiles


def forecast(params: dict[str, float], appliances: list[dict[str, Any]],
             profiles: dict[str, list[float]], start: date, days: int,
             overrides: dict[str, float] | None = None) -> dict[str, Any]:
    """Day-by-day forecast for `days` days starting at `start`.

    overrides: {appliance_id: hours_per_day} replaces the learned weekday habit.
    """
    overrides = overrides or {}
    dates = [start + timedelta(days=i) for i in range(days)]
    weekdays = np.array([d.weekday() for d in dates])
    daily_total = np.zeros(days)
    per_appliance = []

    for a in appliances:
        aid = str(a["id"])
        if aid in overrides:
            hours = np.full(days, float(overrides[aid]))
        else:
            hours = np.array(profiles.get(aid, [0.0] * 7))[weekdays]
        wh = predict_wh(params, hours, a["age_years"], a["power_rating_watts"])
        daily_total += wh
        mean_hours = float(hours.mean())
        per_appliance.append({
            "appliance_id": aid,
            "appliance_name": a["appliance_name"],
            "category": a["category"],
            "power_rating_watts": a["power_rating_watts"],
            "age_years": a["age_years"],
            "is_smart": a["is_smart"],
            "avg_hours_per_day": round(mean_hours, 2),
            "predicted_kwh": round(float(wh.sum()) / 1000, 3),
            # Contribution of each regression term to this appliance's mean daily prediction.
            "drivers_wh": {
                "hours_used": round(params["coefficient_hours"] * mean_hours, 1),
                "age_years": round(params["coefficient_age"] * a["age_years"], 1),
                "power_rating_watts": round(params["coefficient_watts"] * a["power_rating_watts"], 1),
            },
        })

    total_kwh = float(daily_total.sum()) / 1000
    for item in per_appliance:
        item["share"] = (item["predicted_kwh"] / total_kwh) if total_kwh else 0.0
    per_appliance.sort(key=lambda d: d["predicted_kwh"], reverse=True)

    return {
        "start_date": start.isoformat(),
        "days": days,
        "total_kwh": round(total_kwh, 2),
        "daily": [{"date": d.isoformat(), "kwh": round(float(v) / 1000, 3)} for d, v in zip(dates, daily_total)],
        "appliances": per_appliance,
    }
