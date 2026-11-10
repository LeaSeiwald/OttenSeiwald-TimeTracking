"""
tracker.py
Business logic: start/stop timer, manual entries, invoices, statistics.
Connects calculations.py (math) with database.py (storage).
The frontend (app.py) only calls functions from this file.
"""

from datetime import datetime

import database
from calculations import (
    calculate_duration_hours, calculate_cost, calculate_invoice_totals,
    get_rate_for_role, check_budget_status, sum_costs_by,
    parse_datetime, format_datetime, calculate_budget_share, get_month,
)


def _get_person_and_rate(person_id, db_path):
    """Helper: check the person ID and look up the hourly rate of their role."""
    person = database.get_person(person_id, db_path)
    if person is None:
        raise ValueError(f"Unknown personal ID '{person_id}'")
    rate = get_rate_for_role(person["role_name"], database.get_rates(db_path))
    return person, rate


def _check_project(project_id, db_path):
    if database.get_project(project_id, db_path) is None:
        raise ValueError(f"Unknown project ID '{project_id}'")


# -----------------------------
# Timer
# -----------------------------
def start_timer(person_id, project_id, description, billable=True,
                now=None, db_path=database.DB_PATH):
    """Start a timer. A person can only have one running timer at a time."""
    if not description.strip():
        raise ValueError("Please enter an activity description")
    person, rate = _get_person_and_rate(person_id, db_path)
    _check_project(project_id, db_path)
    if database.get_running_entry(person_id, db_path):
        raise ValueError("A timer is already running for this person")

    now = now or datetime.now()  # 'now' can be passed in for testing
    return database.insert_entry(
        person_id, project_id, description, format_datetime(now),
        None, None, rate, billable, db_path,
    )


def stop_timer(person_id, now=None, db_path=database.DB_PATH):
    """Stop the running timer of a person and return the tracked hours."""
    entry = database.get_running_entry(person_id, db_path)
    if entry is None:
        raise ValueError("No running timer for this person")

    now = now or datetime.now()
    start = parse_datetime(entry["start_time"])
    hours = calculate_duration_hours(start, now)
    database.finish_entry(entry["entry_id"], format_datetime(now), hours, db_path)
    return hours


def get_running_timer(person_id, db_path=database.DB_PATH):
    return database.get_running_entry(person_id, db_path)


# -----------------------------
# Manual entry
# -----------------------------
def add_manual_entry(person_id, project_id, description, work_date, hours,
                     billable=True, db_path=database.DB_PATH):
    """Add worked hours manually for a date (datetime.date)."""
    if not description.strip():
        raise ValueError("Please enter an activity description")
    if hours <= 0:
        raise ValueError("Hours must be greater than 0")
    person, rate = _get_person_and_rate(person_id, db_path)
    _check_project(project_id, db_path)

    start = datetime(work_date.year, work_date.month, work_date.day, 0, 0, 0)
    return database.insert_entry(
        person_id, project_id, description, format_datetime(start),
        format_datetime(start), hours, rate, billable, db_path,
    )


# -----------------------------
# Entries with costs
# -----------------------------
def get_entries_with_costs(project_id=None, person_id=None, db_path=database.DB_PATH):
    """Return finished entries, each with an extra 'cost' field."""
    entries = database.get_finished_entries(project_id, person_id, db_path)
    for entry in entries:
        entry["cost"] = calculate_cost(entry["hours"], entry["rate"])
    return entries


# -----------------------------
# Invoice
# -----------------------------
def create_invoice(project_id, person_id=None, db_path=database.DB_PATH):
    """
    Build the data of a customer invoice for a project
    (optionally only for one person). Only billable entries are invoiced.
    """
    project = database.get_project(project_id, db_path)
    if project is None:
        raise ValueError(f"Unknown project ID '{project_id}'")

    entries = get_entries_with_costs(project_id, person_id, db_path)
    billable_entries = [e for e in entries if e["billable"]]

    return {
        "project": project,
        "date": datetime.now().strftime("%d.%m.%Y"),
        "lines": billable_entries,
        "totals": calculate_invoice_totals(billable_entries),
    }


# -----------------------------
# Statistics for the dashboard
# -----------------------------
def get_project_summary(db_path=database.DB_PATH):
    """Hours, costs and budget status per project."""
    entries = get_entries_with_costs(db_path=db_path)
    sums = sum_costs_by(entries, "project_id")

    summary = []
    for project in database.get_projects(db_path):
        used = sums.get(project["project_id"], {"hours": 0, "cost": 0})
        summary.append({
            "project_id": project["project_id"],
            "name": project["name"],
            "hours": round(used["hours"], 2),
            "cost": round(used["cost"], 2),
            "budget": project["budget"],
            "status": check_budget_status(used["cost"], project["budget"]),
        })
    return summary


def get_role_summary(db_path=database.DB_PATH):
    """Hours and costs per role."""
    entries = get_entries_with_costs(db_path=db_path)
    return sum_costs_by(entries, "role_name")


def get_monthly_summary(project_id=None, db_path=database.DB_PATH):
    """
    Hours and costs per project and month, including the share of the budget
    used in that month and the cumulative share up to that month.
    """
    entries = get_entries_with_costs(project_id=project_id, db_path=db_path)
    budgets = {p["project_id"]: p["budget"] for p in database.get_projects(db_path)}

    # 1) sum up per (project, month)
    sums = {}
    for entry in entries:
        key = (entry["project_id"], get_month(entry["start_time"]))
        if key not in sums:
            sums[key] = {"hours": 0, "cost": 0}
        sums[key]["hours"] += entry["hours"]
        sums[key]["cost"] += entry["cost"]

    # 2) add budget shares (sorted -> months in the right order per project)
    result = []
    cumulative = {}
    for project, month in sorted(sums):
        cost = round(sums[(project, month)]["cost"], 2)
        cumulative[project] = cumulative.get(project, 0) + cost
        budget = budgets[project]
        result.append({
            "project_id": project,
            "month": month,
            "hours": round(sums[(project, month)]["hours"], 2),
            "cost": cost,
            "budget_share": calculate_budget_share(cost, budget),
            "cumulative_cost": round(cumulative[project], 2),
            "cumulative_share": calculate_budget_share(cumulative[project], budget),
        })
    return result


def get_budget_overview(project_id=None, db_path=database.DB_PATH):
    """
    Sold budget vs. already worked value, for all projects with a budget
    (or only one project).
    """
    projects = [p for p in get_project_summary(db_path) if p["budget"]]
    if project_id:
        projects = [p for p in projects if p["project_id"] == project_id]

    sold = sum(p["budget"] for p in projects)
    worked = round(sum(p["cost"] for p in projects), 2)
    return {
        "sold": sold,
        "worked": worked,
        "remaining": round(sold - worked, 2),
        "share": calculate_budget_share(worked, sold),
        "status": check_budget_status(worked, sold),
    }