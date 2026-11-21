# claude-automation report

HR dashboard built as a Power BI Project (PBIP) with a TMDL semantic model and a PBIR report, stored as text files in Git.

## Pages

| Page | Id | Focus |
|------|----|-------|
| Emp | `emp` | Headcount, hires, exits, turnover, salary, demographics |
| Dept | `dept` | Department headcount, payroll share, department summary |
| HR (OWN) | `hr_own` | HR's own performance: recruiting, HR cases, HR team ratios |

## Structure

- `claude-automation report.pbip` – open this in Power BI Desktop
- `claude-automation report.SemanticModel/` – TMDL star schema (Dim*/Fact* tables, `_Measures`)
- `claude-automation report.Report/` – PBIR report definition
- `Data/HR/` – sample CSVs
- `tools/generate_hr_data.py` – regenerates the sample data (`python tools/generate_hr_data.py`)

Set the `DataFolder` parameter in `expressions.tmdl` to the local path of `Data/HR`.
