# OttenSeiwald-TimeTracking
Time Tracking Program in Python for Programming (FHTW 2026/27)

User Stories

What is your project about?
project-oriented time-tracking application for small teams and companies. 
Users enter their personal ID, choose a project ID and then either start or stop a timer or put in their working-hours manually for a specific activity. 
All entries are stored in a database. 

Personal IDs are assigned to a person with their role (e.g. Consultant, Developer, Project Manager). 
Each role has its own hourly rate, so the costs of every entry can be calculated automatically. 
At the end of a project, the user can generate customer invoices that list the activities with descriptions, hours and costs per project or person.

Core features
•	User interface with personal ID entry, project ID selection, activity description, start/stop buttons and working-hour entry fields
•	Hourly rates defined per role 
•	Persistent storage of all time entries in a database
•	Automatic cost calculation per entry, per project and per person
•	Invoice generation per project, listing activity descriptions, hours, rates and total amount
•	Unit tests for the core logic (duration and cost calculation, hourly rate assignment, invoice totals)
•	Dashboard showing charts of hours worked and costs per project, as well as distribution by role

Optional features
•	Working time tracking: daily and weekly working hours, overtime and breaks, separate     from billable project time
•	Project budgets: a defined budget per project, with a warning when e.g. 80 % is used
•	Billable vs. non-billable time: e.g. internal meetings that are tracked but not invoiced
•	Export: invoices as PDF, time entries as Excel

