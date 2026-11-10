"""
seed_data.py
Fill the database with example roles, persons, projects and time entries.
Run once: python seed_data.py
(Delete timetracker.db first if you want to start fresh.)
"""

import random
from datetime import date, datetime, timedelta

import database
from calculations import format_datetime

# -----------------------------
# Master data
# -----------------------------
ROLES = [
    ("Project Manager", 120.0),
    ("Senior Developer", 115.0),
    ("Consultant", 110.0),
    ("Data Analyst", 95.0),
    ("Developer", 90.0),
    ("Designer", 85.0),
    ("Tester", 75.0),
    ("Junior Developer", 65.0),
]

PERSONS = [
    ("E001", "Anna Huber", "Project Manager"),
    ("E002", "Max Gruber", "Developer"),
    ("E003", "Sara Wagner", "Consultant"),
    ("E004", "Lukas Bauer", "Senior Developer"),
    ("E005", "Julia Steiner", "Designer"),
    ("E006", "David Moser", "Tester"),
    ("E007", "Lisa Hofer", "Junior Developer"),
    ("E008", "Thomas Berger", "Data Analyst"),
    ("E009", "Katharina Pichler", "Consultant"),
    ("E010", "Florian Mayer", "Developer"),
]

# project_id, name, customer, budget (EUR)
PROJECTS = [
    ("P001", "Webshop Relaunch", "Muster GmbH", 95000.0),
    ("P002", "ERP Integration", "Beispiel AG", 65000.0),
    ("P003", "Customer Portal App", "Alpen Versicherung", 80000.0),
    ("P004", "Sales Dashboard", "Donau Handel KG", 60000.0),
    ("INT", "Internal Meetings", "Internal", None),
]

# Which person works on which projects (weights = how often)
ASSIGNMENTS = {
    "E001": {"P001": 4, "P002": 3, "P003": 3},
    "E002": {"P001": 6, "P003": 2},
    "E003": {"P002": 5, "P004": 3},
    "E004": {"P001": 3, "P002": 4, "P003": 3},
    "E005": {"P001": 5, "P003": 5},
    "E006": {"P001": 4, "P002": 2, "P003": 4},
    "E007": {"P001": 3, "P003": 5},
    "E008": {"P004": 8, "P002": 2},
    "E009": {"P002": 4, "P004": 4},
    "E010": {"P003": 6, "P002": 3},
}

# Typical activities per role
ACTIVITIES = {
    "Project Manager": ["Project planning", "Status meeting with customer",
                        "Risk analysis", "Resource planning", "Steering committee"],
    "Senior Developer": ["Architecture design", "Code review", "Backend development",
                         "API design", "Performance optimisation"],
    "Consultant": ["Requirements workshop", "Process analysis",
                   "Customer meeting", "Concept documentation", "User training"],
    "Data Analyst": ["Data cleaning", "KPI definition", "Building reports",
                     "Data model design", "SQL queries"],
    "Developer": ["Backend development", "Frontend development", "Bug fixing",
                  "Database migration", "Implementing user stories"],
    "Designer": ["UI mockups", "UX research", "Style guide", "Prototype testing",
                 "Icon design"],
    "Tester": ["Test case design", "Manual testing", "Regression tests",
               "Bug reporting", "Test automation"],
    "Junior Developer": ["Frontend development", "Bug fixing", "Writing unit tests",
                         "Documentation", "Pair programming"],
}

START_DATE = date(2026, 8, 31)   # Monday
END_DATE = date(2026, 11, 10)    # -> about 2.5 months


def generate_entries():
    """Create a list of realistic time entries (weekdays only)."""
    random.seed(42)  # same "random" data every time
    roles = dict(ROLES)
    entries = []

    day = START_DATE
    while day <= END_DATE:
        if day.weekday() < 5:  # Monday-Friday
            for person_id, name, role in PERSONS:
                if random.random() < 0.1:  # ~10 % absent (holiday, sick, ...)
                    continue

                current = datetime(day.year, day.month, day.day, 8, 0)
                current += timedelta(minutes=random.choice([0, 15, 30, 45, 60]))

                # Monday: internal jour fixe (not billable)
                if day.weekday() == 0:
                    end = current + timedelta(minutes=45)
                    entries.append((person_id, "INT", "Weekly jour fixe",
                                    current, end, 0.75, roles[role], 0))
                    current = end

                # 2-3 project blocks per day
                projects = list(ASSIGNMENTS[person_id].keys())
                weights = list(ASSIGNMENTS[person_id].values())
                for _ in range(random.choice([2, 2, 3])):
                    project_id = random.choices(projects, weights)[0]
                    minutes = random.choice([45, 60, 90, 120, 150, 180, 210, 240])
                    end = current + timedelta(minutes=minutes)
                    description = random.choice(ACTIVITIES[role])
                    entries.append((person_id, project_id, description, current, end,
                                    round(minutes / 60, 2), roles[role], 1))
                    current = end + timedelta(minutes=random.choice([0, 15, 30]))
        day += timedelta(days=1)

    return entries


def seed(db_path=database.DB_PATH, with_entries=True):
    database.create_tables(db_path)

    for role_name, rate in ROLES:
        database.add_role(role_name, rate, db_path)
    for person_id, name, role in PERSONS:
        database.add_person(person_id, name, role, db_path)
    for project_id, name, customer, budget in PROJECTS:
        database.add_project(project_id, name, customer, budget, db_path)

    if with_entries:
        # executemany inserts all rows at once -> much faster than one by one
        rows = [(p, pr, d, format_datetime(s), format_datetime(e), h, r, b)
                for p, pr, d, s, e, h, r, b in generate_entries()]
        connection = database.get_connection(db_path)
        connection.executemany(
            """INSERT INTO time_entries
               (person_id, project_id, description, start_time, end_time, hours, rate, billable)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        connection.commit()
        connection.close()


if __name__ == "__main__":
    seed()
    print("Example data added to", database.DB_PATH)