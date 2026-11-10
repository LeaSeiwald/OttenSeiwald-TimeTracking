"""
database.py
Everything that talks to the SQLite database.
sqlite3 is built into Python -> no installation needed.
The database is a single file (timetracker.db) in the project folder.
"""

import sqlite3

DB_PATH = "timetracker.db"


def get_connection(db_path=DB_PATH):
    """Open a connection. row_factory lets us access columns by name: row['name']."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(db_path=DB_PATH):
    """Create all tables if they do not exist yet."""
    connection = get_connection(db_path)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS roles (
            role_name   TEXT PRIMARY KEY,
            hourly_rate REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS persons (
            person_id TEXT PRIMARY KEY,
            name      TEXT NOT NULL,
            role_name TEXT NOT NULL REFERENCES roles(role_name)
        );

        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            customer   TEXT NOT NULL,
            budget     REAL
        );

        CREATE TABLE IF NOT EXISTS time_entries (
            entry_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id   TEXT NOT NULL REFERENCES persons(person_id),
            project_id  TEXT NOT NULL REFERENCES projects(project_id),
            description TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            end_time    TEXT,          -- empty while the timer is running
            hours       REAL,          -- empty while the timer is running
            rate        REAL NOT NULL, -- rate is saved with the entry
            billable    INTEGER NOT NULL DEFAULT 1
        );
    """)
    connection.commit()
    connection.close()


# -----------------------------
# Roles, persons, projects
# -----------------------------
def add_role(role_name, hourly_rate, db_path=DB_PATH):
    connection = get_connection(db_path)
    connection.execute(
        "INSERT OR REPLACE INTO roles (role_name, hourly_rate) VALUES (?, ?)",
        (role_name, hourly_rate),
    )
    connection.commit()
    connection.close()


def add_person(person_id, name, role_name, db_path=DB_PATH):
    connection = get_connection(db_path)
    connection.execute(
        "INSERT OR REPLACE INTO persons (person_id, name, role_name) VALUES (?, ?, ?)",
        (person_id, name, role_name),
    )
    connection.commit()
    connection.close()


def add_project(project_id, name, customer, budget=None, db_path=DB_PATH):
    connection = get_connection(db_path)
    connection.execute(
        "INSERT OR REPLACE INTO projects (project_id, name, customer, budget) VALUES (?, ?, ?, ?)",
        (project_id, name, customer, budget),
    )
    connection.commit()
    connection.close()


def get_rates(db_path=DB_PATH):
    """Return all rates as a dict: {'Developer': 90.0, ...}"""
    connection = get_connection(db_path)
    rows = connection.execute("SELECT role_name, hourly_rate FROM roles").fetchall()
    connection.close()
    return {row["role_name"]: row["hourly_rate"] for row in rows}


def get_person(person_id, db_path=DB_PATH):
    """Return one person as a dict, or None if the ID does not exist."""
    connection = get_connection(db_path)
    row = connection.execute(
        "SELECT * FROM persons WHERE person_id = ?", (person_id,)
    ).fetchone()
    connection.close()
    return dict(row) if row else None


def get_persons(db_path=DB_PATH):
    connection = get_connection(db_path)
    rows = connection.execute("SELECT * FROM persons ORDER BY person_id").fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_project(project_id, db_path=DB_PATH):
    connection = get_connection(db_path)
    row = connection.execute(
        "SELECT * FROM projects WHERE project_id = ?", (project_id,)
    ).fetchone()
    connection.close()
    return dict(row) if row else None


def get_projects(db_path=DB_PATH):
    connection = get_connection(db_path)
    rows = connection.execute("SELECT * FROM projects ORDER BY project_id").fetchall()
    connection.close()
    return [dict(row) for row in rows]


# -----------------------------
# Time entries
# -----------------------------
def insert_entry(person_id, project_id, description, start_time, end_time, hours,
                 rate, billable=True, db_path=DB_PATH):
    """Insert a time entry and return its new entry_id."""
    connection = get_connection(db_path)
    cursor = connection.execute(
        """INSERT INTO time_entries
           (person_id, project_id, description, start_time, end_time, hours, rate, billable)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (person_id, project_id, description, start_time, end_time, hours, rate, int(billable)),
    )
    connection.commit()
    entry_id = cursor.lastrowid
    connection.close()
    return entry_id


def finish_entry(entry_id, end_time, hours, db_path=DB_PATH):
    """Set end time and hours of a running entry (used when the timer stops)."""
    connection = get_connection(db_path)
    connection.execute(
        "UPDATE time_entries SET end_time = ?, hours = ? WHERE entry_id = ?",
        (end_time, hours, entry_id),
    )
    connection.commit()
    connection.close()


def get_running_entry(person_id, db_path=DB_PATH):
    """Return the running entry (end_time is empty) of a person, or None."""
    connection = get_connection(db_path)
    row = connection.execute(
        "SELECT * FROM time_entries WHERE person_id = ? AND end_time IS NULL",
        (person_id,),
    ).fetchone()
    connection.close()
    return dict(row) if row else None


def get_finished_entries(project_id=None, person_id=None, db_path=DB_PATH):
    """
    Return all finished entries joined with person, role and project data.
    Optionally filtered by project and/or person.
    """
    sql = """
        SELECT e.*, p.name AS person_name, p.role_name,
               pr.name AS project_name, pr.customer
        FROM time_entries e
        JOIN persons  p  ON e.person_id  = p.person_id
        JOIN projects pr ON e.project_id = pr.project_id
        WHERE e.end_time IS NOT NULL
    """
    params = []
    if project_id:
        sql += " AND e.project_id = ?"
        params.append(project_id)
    if person_id:
        sql += " AND e.person_id = ?"
        params.append(person_id)
    sql += " ORDER BY e.start_time"

    connection = get_connection(db_path)
    rows = connection.execute(sql, params).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def delete_entry(entry_id, db_path=DB_PATH):
    connection = get_connection(db_path)
    connection.execute("DELETE FROM time_entries WHERE entry_id = ?", (entry_id,))
    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_tables()
    print("Database created:", DB_PATH)
