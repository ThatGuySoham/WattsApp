"""Create tables and seed realistic Indian household data.

Usage (from backend/):
    python -m scripts.seed            # create schema, seed only if DB empty
    python -m scripts.seed --reset    # wipe all WattsApp data and reseed
"""
import argparse
import random
import sys
from datetime import date, timedelta

from app.db.connection import apply_schema, close_pool, get_conn, open_pool
from app.db.repository import compute_energy_wh

DAYS_OF_HISTORY = 90
RNG = random.Random(2026)

# (name, category, watts, age, smart, mean_hours, sd_hours, weekend_multiplier, prob_used_per_day)
HOUSEHOLDS = [
    {
        "name": "Sharma Residence",
        "state": "Tamil Nadu",
        "appliances": [
            ("1.5 Ton Inverter AC", "Cooling", 1500, 2, True, 6.0, 1.5, 1.3, 0.95),
            ("Standard Ceiling Fan", "Cooling", 50, 8, False, 12.0, 2.0, 1.1, 1.0),
            ("BLDC Ceiling Fan", "Cooling", 28, 1, True, 11.0, 2.0, 1.1, 1.0),
            ("250L Frost-Free Refrigerator", "Kitchen", 150, 5, False, 10.0, 1.0, 1.0, 1.0),
            ("500W Mixer Grinder", "Kitchen", 500, 4, False, 0.4, 0.15, 1.2, 0.95),
            ("Microwave Oven", "Kitchen", 1200, 3, False, 0.25, 0.1, 1.3, 0.7),
            ("15L Storage Water Heater (Geyser)", "Bathroom", 2000, 6, False, 0.6, 0.2, 1.2, 0.8),
            ("Water Pump (0.5 HP)", "Utility", 375, 9, False, 0.75, 0.2, 1.1, 0.9),
            ("Washing Machine (7kg Top Load)", "Utility", 500, 5, False, 1.0, 0.3, 1.4, 0.45),
            ("Electric Iron", "Utility", 1000, 7, False, 0.3, 0.1, 1.0, 0.6),
            ('43" LED TV', "Entertainment", 100, 3, True, 4.0, 1.2, 1.5, 0.95),
            ("Wi-Fi Router", "Entertainment", 12, 2, False, 24.0, 0.0, 1.0, 1.0),
            ("Laptop", "Work", 65, 2, False, 6.0, 1.5, 0.5, 0.9),
            ("LED Lighting (8 x 9W bulbs)", "Lighting", 72, 2, False, 6.0, 1.0, 1.1, 1.0),
        ],
    },
    {
        "name": "Patil Residence",
        "state": "Maharashtra",
        "appliances": [
            ("Desert Air Cooler", "Cooling", 200, 4, False, 5.0, 1.5, 1.2, 0.7),
            ("Standard Ceiling Fan", "Cooling", 50, 10, False, 10.0, 2.0, 1.1, 1.0),
            ("190L Direct-Cool Refrigerator", "Kitchen", 120, 7, False, 11.0, 1.0, 1.0, 1.0),
            ("750W Mixer Grinder", "Kitchen", 750, 2, False, 0.35, 0.12, 1.2, 0.95),
            ("Induction Cooktop", "Kitchen", 2000, 2, False, 0.6, 0.2, 1.3, 0.8),
            ("3L Instant Water Heater", "Bathroom", 3000, 3, False, 0.3, 0.1, 1.2, 0.9),
            ("Washing Machine (6kg Front Load Inverter)", "Utility", 400, 1, True, 1.2, 0.3, 1.5, 0.4),
            ('32" LED TV', "Entertainment", 60, 6, False, 5.0, 1.5, 1.4, 0.95),
            ("Wi-Fi Router", "Entertainment", 10, 3, False, 24.0, 0.0, 1.0, 1.0),
            ("Desktop PC", "Work", 150, 4, False, 4.0, 1.5, 0.7, 0.85),
            ("LED Tube Lights (3 x 20W)", "Lighting", 60, 3, False, 6.0, 1.0, 1.1, 1.0),
        ],
    },
]


def _hours(mean: float, sd: float, weekend_mult: float, is_weekend: bool, trend: float) -> float:
    mu = mean * (weekend_mult if is_weekend else 1.0) * trend
    h = RNG.gauss(mu, sd) if sd > 0 else mu
    return round(min(24.0, max(0.05, h)), 2)


def seed(reset: bool) -> None:
    apply_schema()
    with get_conn() as conn:
        if reset:
            conn.execute("TRUNCATE regression_models, daily_usage_logs, appliances, households CASCADE")
        count = conn.execute("SELECT COUNT(*) AS n FROM households").fetchone()["n"]
        if count:
            print(f"Database already has {count} household(s); skipping seed. Use --reset to reseed.")
            return

        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=DAYS_OF_HISTORY - 1)
        total_logs = 0
        for hh in HOUSEHOLDS:
            hid = conn.execute(
                "INSERT INTO households (name, state) VALUES (%s, %s) RETURNING id",
                (hh["name"], hh["state"]),
            ).fetchone()["id"]
            for name, cat, watts, age, smart, mean, sd, wk, p in hh["appliances"]:
                aid = conn.execute(
                    """INSERT INTO appliances (household_id, appliance_name, category,
                                               power_rating_watts, age_years, is_smart)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                    (hid, name, cat, watts, age, smart),
                ).fetchone()["id"]
                rows = []
                for i in range(DAYS_OF_HISTORY):
                    d = start + timedelta(days=i)
                    if RNG.random() > p:
                        continue  # appliance not used that day
                    # Gentle seasonal drift: cooling usage eases as monsoon/winter approaches.
                    trend = 1.0 - (0.15 * i / DAYS_OF_HISTORY if cat == "Cooling" else 0.0)
                    h = _hours(mean, sd, wk, d.weekday() >= 5, trend)
                    rows.append((aid, d, h, compute_energy_wh(watts, h, age, smart)))
                with conn.cursor() as cur:
                    cur.executemany(
                        """INSERT INTO daily_usage_logs (appliance_id, date, hours_used, energy_consumed_wh)
                           VALUES (%s, %s, %s, %s)""",
                        rows,
                    )
                total_logs += len(rows)
        print(f"Seeded {len(HOUSEHOLDS)} households, "
              f"{sum(len(h['appliances']) for h in HOUSEHOLDS)} appliances, {total_logs} usage logs "
              f"({start} .. {end}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe and reseed all data")
    args = parser.parse_args()
    open_pool()
    try:
        seed(args.reset)
    except Exception as exc:  # surface failure clearly, non-zero exit
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        close_pool()
