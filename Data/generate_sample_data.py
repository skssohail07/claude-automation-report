"""Generate small sample HR CSVs for the claude-automation report.

Run from the repo root:  python data/generate_sample_data.py
Output: data/csv/departments.csv, employees.csv, dates.csv, hr_cases.csv
Uses only the standard library; random.seed(42) keeps the output deterministic.
"""
import calendar
import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT = Path(__file__).resolve().parent / "csv"
OUT.mkdir(parents=True, exist_ok=True)

# Reporting period covered by dates, leave dates and HR cases
YEAR_START = date(2024, 1, 1)
YEAR_END = date(2025, 12, 31)
# The Date table starts earlier so it covers every hire date (hires begin in 2018)
DATES_START = date(2018, 1, 1)


def write(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def random_day(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


# 1. Departments
departments = [
    (1, "Engineering", 2500000),
    (2, "Sales", 1800000),
    (3, "Finance", 900000),
    (4, "Operations", 1200000),
    (5, "Human Resources", 600000),
]
write("departments.csv", ["DeptID", "DeptName", "Budget"], departments)

# 2. Employees
first_names = ["Aarav", "Anaya", "Rohan", "Isha", "Kabir", "Meera", "Arjun", "Saanvi",
               "Liam", "Emma", "Noah", "Olivia", "Ethan", "Ava", "Priya", "Rahul"]
last_names = ["Sharma", "Iyer", "Nair", "Singh", "Patel", "Gupta", "Rao", "Khan",
              "Smith", "Brown", "Taylor", "Wilson"]
base_salary = {1: 95000, 2: 70000, 3: 75000, 4: 60000, 5: 65000}

employees = []
for emp_id in range(1, 101):
    dept_id = random.choices([1, 2, 3, 4, 5], weights=[35, 25, 12, 18, 10])[0]
    hire = random_day(date(2018, 1, 1), date(2025, 11, 30))
    leave = ""
    if random.random() < 0.15:
        leave_day = random_day(max(hire + timedelta(days=30), YEAR_START), YEAR_END)
        leave = leave_day.isoformat()
    salary = round(base_salary[dept_id] * random.uniform(0.8, 1.4), -2)
    employees.append([
        emp_id,
        f"{random.choice(first_names)} {random.choice(last_names)}",
        random.choice(["Female", "Male"]),
        dept_id,
        hire.isoformat(),
        leave,
        int(salary),
    ])
# Historical leavers: 1-2 per year for 2018-2023, added as extra employees so the
# 2024-2025 figures above are unchanged. A separate generator keeps the main random
# stream (and therefore hr_cases.csv) identical.
hist = random.Random(42)
for leave_year in range(2018, 2024):
    for _ in range(hist.randint(1, 2)):
        earliest_leave = max(date(leave_year, 1, 1), date(2018, 1, 1) + timedelta(days=30))
        leave_day = earliest_leave + timedelta(days=hist.randint(0, (date(leave_year, 12, 31) - earliest_leave).days))
        hire = date(2018, 1, 1) + timedelta(days=hist.randint(0, (leave_day - timedelta(days=30) - date(2018, 1, 1)).days))
        dept_id = hist.choices([1, 2, 3, 4, 5], weights=[35, 25, 12, 18, 10])[0]
        employees.append([
            len(employees) + 1,
            f"{hist.choice(first_names)} {hist.choice(last_names)}",
            hist.choice(["Female", "Male"]),
            dept_id,
            hire.isoformat(),
            leave_day.isoformat(),
            int(round(base_salary[dept_id] * hist.uniform(0.8, 1.4), -2)),
        ])

write("employees.csv",
      ["EmpID", "Name", "Gender", "DeptID", "HireDate", "LeaveDate", "Salary"], employees)

# 3. Dates: every day from 2018 to the end of 2025
dates = []
d = DATES_START
while d <= YEAR_END:
    dates.append([d.isoformat(), d.year, d.month, calendar.month_name[d.month]])
    d += timedelta(days=1)
write("dates.csv", ["Date", "Year", "Month", "MonthName"], dates)

# 4. HR cases: OnTime = 1 when closed within the 5-day target
case_types = ["Payroll", "Leave", "Benefits", "Grievance", "Onboarding", "Policy"]
SLA_DAYS = 5
cases = []
for case_id in range(1, 201):  # about 100 per year
    days_to_close = random.randint(1, 12)
    cases.append([
        case_id,
        random.randint(1, 5),
        random.choice(case_types),
        random_day(YEAR_START, YEAR_END).isoformat(),
        days_to_close,
        1 if days_to_close <= SLA_DAYS else 0,
    ])
write("hr_cases.csv",
      ["CaseID", "DeptID", "CaseType", "OpenDate", "DaysToClose", "OnTime"], cases)
