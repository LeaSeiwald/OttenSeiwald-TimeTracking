"""
app.py
Frontend of the time tracker, built with Streamlit.
Start with:  streamlit run app.py
The browser opens automatically (http://localhost:8501).

Note: Streamlit runs this whole file again after EVERY click.
That's why all data lives in the database, not in normal variables.
"""

from datetime import date

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import database
import tracker
from seed_data import seed

# -----------------------------
# Setup
# -----------------------------
st.set_page_config(page_title="Time Tracker", page_icon="⏱️", layout="wide")

database.create_tables()
if not database.get_persons():  # first start: add example data
    seed()

persons = database.get_persons()
projects = database.get_projects()
project_ids = [p["project_id"] for p in projects]
project_labels = {p["project_id"]: f'{p["project_id"]} – {p["name"]}' for p in projects}

page = st.sidebar.radio("Navigation", ["Time tracking", "Entries", "Invoice", "Dashboard"])


# -----------------------------
# Page 1: Time tracking
# -----------------------------
if page == "Time tracking":
    st.title("Time tracking")

    person_id = st.text_input("Personal ID", placeholder="e.g. E001")
    person = database.get_person(person_id) if person_id else None

    if person_id and person is None:
        st.error("Unknown personal ID")

    if person:
        st.success(f'Hello {person["name"]} ({person["role_name"]})')

        running = tracker.get_running_timer(person_id)

        # --- Timer ---
        st.subheader("Timer")
        # Show the message from the last stop (survives st.rerun())
        if "last_saved" in st.session_state:
            st.success(st.session_state.pop("last_saved"))

        if running:
            st.info(f'Timer running since {running["start_time"]} – '
                    f'{running["project_id"]}: {running["description"]}')
            if st.button("⏹️ Stop timer", type="primary"):
                hours = tracker.stop_timer(person_id)
                minutes = round(hours * 60)
                st.session_state["last_saved"] = f"Saved: {hours} hours ({minutes} min)"
                st.rerun()
        else:
            project_id = st.selectbox("Project", project_ids,
                                      format_func=lambda pid: project_labels[pid])
            description = st.text_input("Activity description")
            billable = st.checkbox("Billable", value=True)
            if st.button("▶️ Start timer", type="primary"):
                try:
                    tracker.start_timer(person_id, project_id, description, billable)
                    st.rerun()
                except ValueError as error:
                    st.error(error)

        # --- Manual entry ---
        st.subheader("Manual entry")
        with st.form("manual_entry", clear_on_submit=True):
            m_project = st.selectbox("Project", project_ids,
                                     format_func=lambda pid: project_labels[pid])
            m_description = st.text_input("Activity description")
            m_date = st.date_input("Date", value=date.today())
            m_hours = st.number_input("Hours", min_value=0.0, step=0.25)
            m_billable = st.checkbox("Billable", value=True)
            if st.form_submit_button("Save entry"):
                try:
                    tracker.add_manual_entry(person_id, m_project, m_description,
                                             m_date, m_hours, m_billable)
                    st.success("Entry saved")
                except ValueError as error:
                    st.error(error)


# -----------------------------
# Page 2: Entries
# -----------------------------
elif page == "Entries":
    st.title("Time entries")

    col1, col2 = st.columns(2)
    filter_project = col1.selectbox("Project", ["All"] + project_ids)
    filter_person = col2.selectbox("Person", ["All"] + [p["person_id"] for p in persons])

    entries = tracker.get_entries_with_costs(
        project_id=None if filter_project == "All" else filter_project,
        person_id=None if filter_person == "All" else filter_person,
    )

    if not entries:
        st.info("No entries yet")
    else:
        df = pd.DataFrame(entries)
        df = df[["entry_id", "start_time", "person_name", "role_name", "project_id",
                 "description", "hours", "rate", "cost", "billable"]]
        st.dataframe(df, hide_index=True, width="stretch")

        col1, col2 = st.columns(2)
        col1.metric("Total hours", f'{df["hours"].sum():.2f}')
        col2.metric("Total costs", f'€ {df["cost"].sum():,.2f}')

        st.download_button("Download as CSV", df.to_csv(index=False, sep=";"),
                           file_name="time_entries.csv")

        with st.expander("Delete an entry"):
            delete_id = st.number_input("Entry ID", min_value=1, step=1)
            if st.button("Delete"):
                database.delete_entry(int(delete_id))
                st.rerun()


# -----------------------------
# Page 3: Invoice
# -----------------------------
elif page == "Invoice":
    st.title("Invoice")

    col1, col2 = st.columns(2)
    project_id = col1.selectbox("Project", project_ids,
                                format_func=lambda pid: project_labels[pid])
    person_choice = col2.selectbox("Person (optional)",
                                   ["All"] + [p["person_id"] for p in persons])

    invoice = tracker.create_invoice(
        project_id, None if person_choice == "All" else person_choice)
    project = invoice["project"]
    totals = invoice["totals"]

    st.markdown(f'**Customer:** {project["customer"]}  \n'
                f'**Project:** {project["project_id"]} – {project["name"]}  \n'
                f'**Date:** {invoice["date"]}')

    if not invoice["lines"]:
        st.info("No billable entries for this project")
    else:
        df = pd.DataFrame(invoice["lines"])
        df["date"] = df["start_time"].str[:10]
        df = df[["date", "description", "person_name", "role_name", "hours", "rate", "cost"]]
        df.columns = ["Date", "Activity", "Person", "Role", "Hours", "Rate (€)", "Amount (€)"]
        st.dataframe(df, hide_index=True, width="stretch")

        st.markdown(f'Total hours: **{totals["total_hours"]}**  \n'
                    f'Net: **€ {totals["net"]:,.2f}**  \n'
                    f'VAT 20 %: **€ {totals["vat"]:,.2f}**  \n'
                    f'### Total: € {totals["gross"]:,.2f}')

        st.download_button("Download invoice (CSV)", df.to_csv(index=False, sep=";"),
                           file_name=f"invoice_{project_id}.csv")


# -----------------------------
# Page 4: Dashboard
# -----------------------------
elif page == "Dashboard":
    st.title("Dashboard")

    entries = pd.DataFrame(tracker.get_entries_with_costs())
    if entries.empty:
        st.info("No entries yet")
        st.stop()

    summary = pd.DataFrame(tracker.get_project_summary())
    monthly = pd.DataFrame(tracker.get_monthly_summary())
    entries["month"] = entries["start_time"].str[:7]

    # --- Filters ---
    col1, col2 = st.columns(2)
    project_filter = col1.selectbox(
        "Project", ["All"] + project_ids,
        format_func=lambda pid: "All projects" if pid == "All" else project_labels[pid])
    all_months = sorted(entries["month"].unique())
    month_filter = col2.multiselect("Months", all_months, default=all_months)

    if project_filter != "All":
        summary = summary[summary["project_id"] == project_filter]
        monthly = monthly[monthly["project_id"] == project_filter]
        entries = entries[entries["project_id"] == project_filter]

    # Same color for each project in every chart
    palette = plt.get_cmap("tab10").colors
    project_colors = {pid: palette[i % 10] for i, pid in enumerate(project_ids)}

    monthly_filtered = monthly[monthly["month"].isin(month_filter)]
    entries_filtered = entries[entries["month"].isin(month_filter)]

    # --- Budget overview (always total up to today) ---
    st.subheader("Budget overview")
    overview = tracker.get_budget_overview(
        None if project_filter == "All" else project_filter)

    if overview["sold"] == 0:
        st.info("This project has no budget")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Budget sold", f'€ {overview["sold"]:,.0f}')
        col2.metric("Already worked", f'€ {overview["worked"]:,.0f}')
        col3.metric("Remaining", f'€ {overview["remaining"]:,.0f}')
        col4.metric("Budget used", f'{overview["share"]} %')
        st.progress(min(overview["share"] / 100, 1.0))

        # Budget warnings
        for _, row in summary.iterrows():
            if row["status"] == "warning":
                st.warning(f'{row["name"]}: over 80 % of the budget used')
            elif row["status"] == "exceeded":
                st.error(f'{row["name"]}: budget exceeded!')

        # Budget vs. worked per project
        budgeted = summary[summary["budget"].notna()]
        colors = {"ok": "#55A868", "warning": "#DD8452", "exceeded": "#C44E52"}
        fig, ax = plt.subplots(figsize=(8, 0.6 * len(budgeted) + 1))
        ax.barh(budgeted["project_id"], budgeted["budget"], color="#DDDDDD", label="Budget")
        ax.barh(budgeted["project_id"], budgeted["cost"],
                color=[colors[s] for s in budgeted["status"]], height=0.5, label="Worked")
        for _, row in budgeted.iterrows():
            share = round(row["cost"] / row["budget"] * 100, 1)
            ax.text(max(row["cost"], row["budget"]) * 1.01, row["project_id"],
                    f"{share} %", va="center")
        ax.set_xlim(0, max(budgeted["budget"].max(), budgeted["cost"].max()) * 1.15)
        ax.set_xlabel("EUR")
        ax.invert_yaxis()
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
        st.pyplot(fig)

    # --- Monthly view ---
    st.subheader("Costs per month")
    col1, col2 = st.columns(2)

    with col1:
        pivot = monthly_filtered.pivot_table(index="month", columns="project_id",
                                             values="cost", aggfunc="sum", fill_value=0)
        fig, ax = plt.subplots()
        pivot.plot(kind="bar", stacked=True, ax=ax,
                   color=[project_colors[pid] for pid in pivot.columns])
        ax.set_xlabel("")
        ax.set_ylabel("EUR")
        ax.tick_params(axis="x", rotation=0)
        ax.legend(title="Project")
        st.pyplot(fig)

    with col2:
        # Cumulative share of the budget per month
        with_budget = monthly_filtered[monthly_filtered["cumulative_share"].notna()]
        fig, ax = plt.subplots()
        for project_id, group in with_budget.groupby("project_id"):
            ax.plot(group["month"], group["cumulative_share"], marker="o",
                    label=project_id, color=project_colors[project_id])
        ax.axhline(80, color="#DD8452", linestyle="--", linewidth=1)
        ax.axhline(100, color="#C44E52", linestyle="--", linewidth=1)
        ax.set_ylabel("% of budget used (cumulative)")
        if not with_budget.empty:
            ax.legend(title="Project")
        st.pyplot(fig)

    table = monthly_filtered.rename(columns={
        "project_id": "Project", "month": "Month", "hours": "Hours", "cost": "Cost (€)",
        "budget_share": "% of budget (month)", "cumulative_cost": "Cost total (€)",
        "cumulative_share": "% of budget (total)"})
    st.dataframe(table, hide_index=True, width="stretch")

    # --- Hours and roles (selected months) ---
    st.subheader("👥 Hours and roles")
    col1, col2 = st.columns(2)

    with col1:
        hours = entries_filtered.groupby("project_id")["hours"].sum()
        fig, ax = plt.subplots()
        ax.bar(hours.index, hours.values,
               color=[project_colors[pid] for pid in hours.index])
        ax.set_ylabel("Hours")
        ax.set_title("Hours per project")
        st.pyplot(fig)

    with col2:
        roles = entries_filtered.groupby("role_name")["hours"].sum()
        fig, ax = plt.subplots()
        ax.pie(roles.values, labels=roles.index, autopct="%1.0f%%")
        ax.set_title("Hours by role")
        st.pyplot(fig)