"""Analytics orchestration: training, staleness checks, forecasting, bill estimation."""
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.config import MODEL_STALE_HOURS
from app.db import repository as repo
from app.ml import regression as ml
from app.services import tariff


class NotFoundError(LookupError):
    pass


def _require_household(household_id: str) -> dict[str, Any]:
    hh = repo.get_household(household_id)
    if not hh:
        raise NotFoundError(f"Household {household_id} not found")
    return hh


def train_household(household_id: str) -> dict[str, Any]:
    _require_household(household_id)
    result = ml.train(repo.training_rows(household_id))
    model = repo.upsert_model(household_id, result.params)
    return {"model": model, "diagnostics": result.diagnostics}


def _is_stale(model: dict[str, Any] | None) -> bool:
    if model is None:
        return True
    age = datetime.now(timezone.utc) - model["last_trained"]
    return age > timedelta(hours=MODEL_STALE_HOURS)


def ensure_model(household_id: str) -> dict[str, Any]:
    """Return a fresh model, retraining if missing or older than MODEL_STALE_HOURS."""
    model = repo.get_model(household_id)
    if _is_stale(model):
        model = train_household(household_id)["model"]
    return model


def model_report(household_id: str) -> dict[str, Any]:
    _require_household(household_id)
    model = ensure_model(household_id)
    df_rows = repo.training_rows(household_id)
    diag = ml.diagnostics(ml.to_frame(df_rows), model)
    return {"model": model, "diagnostics": diag}


def predict(household_id: str, days: int, overrides: dict[str, float] | None,
            include_bill: bool = True) -> dict[str, Any]:
    hh = _require_household(household_id)
    model = ensure_model(household_id)
    appliances = repo.list_appliances(household_id)
    if overrides:
        unknown = set(overrides) - {str(a["id"]) for a in appliances}
        if unknown:
            raise NotFoundError(f"Unknown appliance ids for this household: {', '.join(sorted(unknown))}")
    profiles = ml.weekday_profiles(repo.training_rows(household_id), appliances)
    fc = ml.forecast(model, appliances, profiles, date.today(), days, overrides)

    result: dict[str, Any] = {
        "household": hh,
        "model": model,
        "forecast": fc,
        "guzzlers": fc["appliances"][:3],
    }
    if include_bill:
        result["bill"] = tariff.calculate_bill(hh["state"], fc["total_kwh"])
    return result


def history(household_id: str, days: int) -> dict[str, Any]:
    _require_household(household_id)
    rows = repo.daily_totals(household_id, days)
    daily = [{"date": r["date"].isoformat(), "kwh": round(r["wh"] / 1000, 3)} for r in rows]
    return {"days": days, "total_kwh": round(sum(d["kwh"] for d in daily), 2), "daily": daily}
