"""
calculations.py
Pure calculation logic of the time tracker.
No database, no user interface -> easy to test with unittest.
"""

import math
from datetime import datetime

# -----------------------------
# Constants
# -----------------------------
VAT_RATE = 0.20              # Austrian VAT (20 %)
BUDGET_WARNING_LEVEL = 0.80  # warn when 80 % of a project budget is used
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# -----------------------------
# Duration
# -----------------------------
def calculate_duration_minutes(start, end):
    """Return the duration in full minutes. Every started minute counts (rounded up)."""
    if end < start:
        raise ValueError("End time must not be before start time")
    seconds = (end - start).total_seconds()
    return math.ceil(seconds / 60)


def calculate_duration_hours(start, end):
    """Return the duration in hours (rounded to 2 decimals), e.g. 1 minute = 0.02 h."""
    minutes = calculate_duration_minutes(start, end)
    return round(minutes / 60, 2)


def parse_datetime(text):
    """Convert a string like '2026-11-10 09:00:00' into a datetime object."""
    return datetime.strptime(text, DATETIME_FORMAT)


def format_datetime(dt):
    """Convert a datetime object into a string for the database."""
    return dt.strftime(DATETIME_FORMAT)

# -----------------------------
# Rates and costs
# -----------------------------
def get_rate_for_role(role, rates):
    """Return the hourly rate of a role from a dict like {'Developer': 90.0}."""
    if role not in rates:
        raise KeyError(f"No hourly rate defined for role '{role}'")
    return rates[role]


def calculate_cost(hours, rate):
    """Return the cost of an entry: hours * hourly rate (rounded to 2 decimals)."""
    if hours < 0 or rate < 0:
        raise ValueError("Hours and rate must not be negative")
    return round(hours * rate, 2)


# -----------------------------
# Invoice totals
# -----------------------------
def calculate_invoice_totals(entries):
    """
    Calculate the totals of an invoice.
    entries: list of dicts, each with the keys 'hours' and 'rate'.
    Returns a dict with total_hours, net, vat and gross.
    """
    total_hours = 0
    net = 0
    for entry in entries:
        total_hours += entry["hours"]
        net += calculate_cost(entry["hours"], entry["rate"])

    net = round(net, 2)
    vat = round(net * VAT_RATE, 2)
    return {
        "total_hours": round(total_hours, 2),
        "net": net,
        "vat": vat,
        "gross": round(net + vat, 2),
    }


def sum_costs_by(entries, key):
    """
    Sum up hours and costs grouped by a key, e.g. 'project_id' or 'person_name'.
    Returns a dict like {'P001': {'hours': 5.0, 'cost': 450.0}}.
    """
    result = {}
    for entry in entries:
        group = entry[key]
        if group not in result:
            result[group] = {"hours": 0, "cost": 0}
        result[group]["hours"] += entry["hours"]
        result[group]["cost"] += calculate_cost(entry["hours"], entry["rate"])
    return result


# -----------------------------
# Budget (optional feature)
# -----------------------------
def check_budget_status(used, budget):
    """
    Return 'ok', 'warning' (>= 80 %) or 'exceeded' (> 100 %).
    Returns 'no budget' if the project has no budget.
    """
    if budget is None or budget <= 0:
        return "no budget"
    share = used / budget
    if share > 1:
        return "exceeded"
    if share >= BUDGET_WARNING_LEVEL:
        return "warning"
    return "ok"

def calculate_budget_share(used, budget):
    """Return how many percent of the budget are used, e.g. 85.3. None if no budget."""
    if budget is None or budget <= 0:
        return None
    return round(used / budget * 100, 1)


# -----------------------------
# Months
# -----------------------------
def get_month(datetime_text):
    """Return the month of a datetime string: '2026-11-10 09:00:00' -> '2026-11'."""
    return datetime_text[:7]

if __name__ == "__main__":
    # Only runs when this file is executed directly
    start = parse_datetime("2026-11-10 09:00:00")
    end = parse_datetime("2026-11-10 11:30:00")
    hours = calculate_duration_hours(start, end)
    print("Hours:", hours)
    print("Cost:", calculate_cost(hours, 90))
