# claude-automation report

An HR dashboard built as a Power BI Project (PBIP). The semantic model is TMDL and the report is PBIR, so everything is plain text and versioned in Git.

## What the dashboard shows

| Page | What it answers |
|------|-----------------|
| **Emp** | How many people work here and how that is changing: Headcount, Hires, Leavers, Attrition %, Female %, headcount by month, gender split and an employee list. |
| **Dept** | How each department is staffed and funded: Headcount, Budget, Budget Used % (salary cost against budget), Avg Salary, Attrition % by department and a department summary table. |
| **HR (OWN)** | How well the HR function itself is performing: HR Cases, Avg Days to Close, SLA Met %, Staff per HR Person, cases by month and SLA by case type. |

Each page has a Year slicer; Emp and HR (OWN) also have a Department slicer. Headcount is calculated from each employee's hire and leave dates against the last day of the selected period, so it is correct for any year or month.

## Data files

Four CSV files in `Data/csv/`, generated with a fixed seed so they are the same on every machine:

| File | Rows | Columns |
|------|------|---------|
| `departments.csv` | 5 | DeptID, DeptName, Budget |
| `employees.csv` | 107 | EmpID, Name, Gender, DeptID, HireDate, LeaveDate (blank if still employed), Salary |
| `dates.csv` | 731 | Date, Year, Month, MonthName (every day of 2024 and 2025) |
| `hr_cases.csv` | 200 | CaseID, DeptID, CaseType, OpenDate, DaysToClose, OnTime (1 if closed within 5 days) |

In the model these load as the `Department`, `Employee`, `Date` and `HRCase` tables. All measures live in a separate `_Measures` table.

## Open the project

1. Install [Power BI Desktop](https://powerbi.microsoft.com/desktop/) (a recent version that supports PBIP and PBIR).
2. Clone this repository.
3. Set `DataFolder` (see below) to where you cloned it.
4. Double-click `claude-automation report.pbip`, or use **File > Open** in Power BI Desktop.
5. If a banner says tables have no data, click **Refresh now**. The data cache is not stored in Git, so the first open always needs a refresh.

## Set DataFolder

`DataFolder` is a text parameter holding the full path to the CSV folder, ending with a backslash. Every table query reads `DataFolder & "<file>.csv"`.

Either edit `claude-automation report.SemanticModel/definition/expressions.tmdl` before opening:

```
expression DataFolder = "C:\path\to\repo\Data\csv\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
```

or, in Power BI Desktop, go to **Home > Transform data > Edit parameters**, change `DataFolder` and click **Refresh**.

## Regenerate the data

```
python Data/generate_sample_data.py
```

The script uses only the Python standard library and `random.seed(42)`, so rerunning it produces identical files. To get different data, change the seed or the settings at the top of the script, then refresh in Power BI Desktop.

## Validate the project

```
python tools/validate_project.py
```

This checks that every JSON file parses, every table file is listed in `model.tmdl`, relationships and visuals only refer to tables, columns and measures that exist, TMDL is indented with tabs, and the report has exactly the pages Emp, Dept and HR (OWN). It exits with code 1 if anything fails, so it can run in CI.

## Repository layout

```
claude-automation report.pbip            open this in Power BI Desktop
claude-automation report.SemanticModel/  TMDL model: tables, relationships, measures, DataFolder
claude-automation report.Report/         PBIR report: pages emp, dept, hr_own
Data/generate_sample_data.py             sample data generator
Data/csv/                                the four CSV files
tools/validate_project.py                project validation
```
