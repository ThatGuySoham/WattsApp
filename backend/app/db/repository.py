"""SQL operations for all WattsApp tables. Pure data access — no HTTP/ML concerns."""
from datetime import date
from typing import Any

from app.db.connection import get_conn

# Efficiency model agreed for energy_consumed_wh:
#   factor = (1 + 0.02 * age_years) * (0.85 if is_smart else 1.0)
AGE_PENALTY_PER_YEAR = 0.02
SMART_FACTOR = 0.85


def efficiency_factor(age_years: int, is_smart: bool) -> float:
    return (1 + AGE_PENALTY_PER_YEAR * age_years) * (SMART_FACTOR if is_smart else 1.0)


def compute_energy_wh(power_rating_watts: int, hours_used: float, age_years: int, is_smart: bool) -> float:
    return round(power_rating_watts * hours_used * efficiency_factor(age_years, is_smart), 2)


# ---------------------------------------------------------------- households
def list_households() -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name, state, created_at FROM households ORDER BY created_at, name"
        ).fetchall()


def get_household(household_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name, state, created_at FROM households WHERE id = %s", (household_id,)
        ).fetchone()


# ---------------------------------------------------------------- appliances
_APPLIANCE_STATS_SQL = """
SELECT a.id, a.household_id, a.appliance_name, a.category, a.power_rating_watts,
       a.age_years, a.is_smart,
       COALESCE(s.avg_hours, 0)      AS avg_hours_per_day,
       COALESCE(s.total_wh, 0)       AS energy_last_30d_wh,
       s.last_logged
FROM appliances a
LEFT JOIN LATERAL (
    SELECT AVG(l.hours_used) AS avg_hours,
           SUM(l.energy_consumed_wh) AS total_wh,
           MAX(l.date) AS last_logged
    FROM daily_usage_logs l
    WHERE l.appliance_id = a.id
      AND l.date > (SELECT COALESCE(MAX(date), CURRENT_DATE) FROM daily_usage_logs l2
                    WHERE l2.appliance_id = a.id) - INTERVAL '30 days'
) s ON TRUE
"""


def list_appliances(household_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            _APPLIANCE_STATS_SQL + " WHERE a.household_id = %s ORDER BY a.category, a.appliance_name",
            (household_id,),
        ).fetchall()


def get_appliance(appliance_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        return conn.execute(_APPLIANCE_STATS_SQL + " WHERE a.id = %s", (appliance_id,)).fetchone()


def create_appliance(household_id: str, data: dict[str, Any]) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """INSERT INTO appliances (household_id, appliance_name, category,
                                       power_rating_watts, age_years, is_smart)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
            (household_id, data["appliance_name"], data["category"],
             data["power_rating_watts"], data["age_years"], data["is_smart"]),
        ).fetchone()
    return get_appliance(str(row["id"]))


def delete_appliance(appliance_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM appliances WHERE id = %s", (appliance_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------- usage logs
def create_usage_log(appliance: dict[str, Any], log_date: date, hours_used: float) -> dict[str, Any]:
    energy = compute_energy_wh(
        appliance["power_rating_watts"], hours_used, appliance["age_years"], appliance["is_smart"]
    )
    with get_conn() as conn:
        return conn.execute(
            """INSERT INTO daily_usage_logs (appliance_id, date, hours_used, energy_consumed_wh)
               VALUES (%s, %s, %s, %s)
               RETURNING id, appliance_id, date, hours_used, energy_consumed_wh""",
            (appliance["id"], log_date, hours_used, energy),
        ).fetchone()


def daily_totals(household_id: str, days: int) -> list[dict[str, Any]]:
    """Household energy per day for the most recent `days` days that have data."""
    with get_conn() as conn:
        return conn.execute(
            """WITH hh AS (
                   SELECT l.date, SUM(l.energy_consumed_wh) AS wh
                   FROM daily_usage_logs l JOIN appliances a ON a.id = l.appliance_id
                   WHERE a.household_id = %s
                   GROUP BY l.date
               )
               SELECT date, wh FROM hh
               WHERE date > (SELECT MAX(date) FROM hh) - %s::int
               ORDER BY date""",
            (household_id, days),
        ).fetchall()


def training_rows(household_id: str) -> list[dict[str, Any]]:
    """Joined log + appliance features used to fit the regression."""
    with get_conn() as conn:
        return conn.execute(
            """SELECT l.id AS log_id, l.date, l.hours_used, l.energy_consumed_wh,
                      a.id AS appliance_id, a.appliance_name, a.category,
                      a.age_years, a.power_rating_watts, a.is_smart
               FROM daily_usage_logs l JOIN appliances a ON a.id = l.appliance_id
               WHERE a.household_id = %s
               ORDER BY l.date""",
            (household_id,),
        ).fetchall()


# ---------------------------------------------------------------- regression models
def get_model(household_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        return conn.execute(
            """SELECT id, household_id, coefficient_hours, coefficient_age, coefficient_watts,
                      intercept, r_squared, last_trained
               FROM regression_models WHERE household_id = %s""",
            (household_id,),
        ).fetchone()


def upsert_model(household_id: str, params: dict[str, float]) -> dict[str, Any]:
    with get_conn() as conn:
        return conn.execute(
            """INSERT INTO regression_models (household_id, coefficient_hours, coefficient_age,
                                              coefficient_watts, intercept, r_squared, last_trained)
               VALUES (%(hid)s, %(ch)s, %(ca)s, %(cw)s, %(ic)s, %(r2)s, now())
               ON CONFLICT (household_id) DO UPDATE SET
                   coefficient_hours = EXCLUDED.coefficient_hours,
                   coefficient_age   = EXCLUDED.coefficient_age,
                   coefficient_watts = EXCLUDED.coefficient_watts,
                   intercept         = EXCLUDED.intercept,
                   r_squared         = EXCLUDED.r_squared,
                   last_trained      = now()
               RETURNING id, household_id, coefficient_hours, coefficient_age, coefficient_watts,
                         intercept, r_squared, last_trained""",
            {"hid": household_id, "ch": params["coefficient_hours"], "ca": params["coefficient_age"],
             "cw": params["coefficient_watts"], "ic": params["intercept"], "r2": params["r_squared"]},
        ).fetchone()
