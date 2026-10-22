"""Indian electricity tariff calculation (telescopic slabs)."""
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

TARIFF_FILE = Path(__file__).resolve().parent.parent / "tariffs.json"


class UnknownStateError(KeyError):
    pass


@lru_cache(maxsize=1)
def load_tariffs() -> dict[str, Any]:
    data = json.loads(TARIFF_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def get_tariff(state: str) -> dict[str, Any]:
    tariffs = load_tariffs()
    if state not in tariffs:
        raise UnknownStateError(f"No tariff configured for state '{state}'. Supported: {', '.join(tariffs)}")
    return tariffs[state]


def calculate_bill(state: str, units: float) -> dict[str, Any]:
    tariff = get_tariff(state)
    units = max(0.0, float(units))
    breakdown = []
    lower = 0.0
    energy_charge = 0.0
    for slab in tariff["slabs"]:
        upper = slab["upto"]
        if units <= lower:
            break
        span_top = units if upper is None else min(units, float(upper))
        slab_units = span_top - lower
        amount = slab_units * slab["rate"]
        energy_charge += amount
        breakdown.append({
            "from_unit": int(lower) + 1 if lower else 0,
            "to_unit": upper,
            "units": round(slab_units, 2),
            "rate": slab["rate"],
            "amount": round(amount, 2),
        })
        if upper is None:
            break
        lower = float(upper)

    fixed = float(tariff["fixed_charge_inr"])
    waived = tariff.get("free_if_units_at_most") is not None and units <= tariff["free_if_units_at_most"]
    total = 0.0 if waived else energy_charge + fixed
    return {
        "state": state,
        "discom": tariff["discom"],
        "billing_cycle_days": tariff["billing_cycle_days"],
        "units": round(units, 2),
        "energy_charge_inr": round(energy_charge, 2),
        "fixed_charge_inr": round(fixed, 2),
        "subsidy_applied": waived,
        "total_inr": round(total, 2),
        "slabs": breakdown,
    }
