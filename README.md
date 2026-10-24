# FlowGuard AI

A Windows desktop prototype that validates Excel updates before
publishing an approved workbook for Power BI.

It combines local data profiling, baseline comparison,
guarded workbook publishing, experimental Power BI Desktop
automation, and on-demand local AI review.

## Demo workflow

1. A user saves changes to an incoming Excel workbook.
2. FlowGuard detects the change and waits for the file to stabilize.
3. The workbook is checked against a reviewed structural baseline.
4. If checks fail or require review, publishing and refresh are skipped.
5. If checks pass, the previous approved workbook is backed up
   and the validated copy is published.
6. Optional desktop automation triggers Power BI refresh and observes
   the refresh dialog and a report timestamp.

## Implemented features

- Desktop interface for file selection and monitoring controls.
- Excel worksheet, column-type, and missing-value profiling.
- Reviewed structural baselines.
- Detection of missing sheets, missing columns, new value types,
  and stored Excel cell errors.
- Approved-workbook publishing with backups.
- Single-instance monitoring lock within the project directory.
- Cooperative stopping between monitoring cycles.
- Experimental Power BI refresh triggering and observation.
- On-demand AI review of worksheet metadata through local Ollama.
- User-confirmed removal of outer whitespace in selected text columns.
- Separate corrected copies with correction audit records.

## Local AI

The demo uses `qwen3:1.7b` through Ollama.

AI review receives worksheet metadata such as column names,
observed types, and missing-value counts. It does not receive
cell values in the implemented review workflow.

AI suggestions are checked against supported suggestion types
and observed metadata. They do not automatically become rules
or modify workbooks.

## Privacy

- Workbook inspection and correction run locally.
- AI requests target `http://127.0.0.1:11434`.
- Run Ollama with cloud features disabled.
- Metadata can still be sensitive.
- Reports, profiles, correction copies, and audit files stay local
  and should not be committed to Git.
- Audit records contain cell locations and actions, not old or new values.
- Use synthetic or explicitly authorized data for demonstrations.

## Requirements

- Windows.
- Python with Tkinter.
- Dependencies listed in `requirements.txt`.
- Power BI Desktop for the optional refresh demonstration.
- Ollama and the local model for AI review.

The development environment used Python 3.15. A compatibility warning
from comtypes was observed; broader Python and Windows compatibility
has not been established.

## Installation

From the repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For local AI, install Ollama separately and download:

```powershell
ollama pull qwen3:1.7b
```

Quit any existing Ollama server before starting a local-only session:

```powershell
$env:OLLAMA_NO_CLOUD = "1"
ollama serve
```

Confirm that the server logs show:

```text
Ollama cloud disabled: true
```

Keep that server terminal open.

## Prepare a demo dataset

Use a tabular `.xlsx` workbook with column headers in the first row.

Create these directories if needed:

```powershell
New-Item -ItemType Directory -Force -Path data/incoming, data/approved, reports/baselines
```

Place the source workbook in `data/incoming`.

Generate its profile:

```powershell
.\.venv\Scripts\python.exe src/inspect_excel.py data/incoming/FlowBI_Project_Management.xlsx
```

Review the workbook structure before creating the baseline:

```powershell
.\.venv\Scripts\python.exe src/create_baseline.py reports/data_profile.json reports/baselines/projects_v1.json
```

The baseline records an observed structure; it does not certify
the business correctness of the data.

Keep the baseline unchanged during error-detection tests.

## Run the desktop interface

```powershell
.\.venv\Scripts\python.exe src/desktop.py
```

Select:

- Source Excel: the workbook in `data/incoming`.
- Reviewed baseline: the corresponding baseline JSON.
- Approved Excel: a separate destination in `data/approved`.

`Check Data` validates without publishing.

`Start Monitoring` waits for a new source-file change.
It does not automatically publish the initial file at startup.

`Stop` requests shutdown after the current cycle finishes.

## Power BI demo setup

Connect the report to the approved workbook, not the incoming workbook.

The current automation targets:

```text
FlowBI - Power BI Desktop
```

It depends on the tested ribbon layout and refresh-button location.
Keep Power BI maximized on the Home tab.

The timestamp reader expects a visible card titled:

```text
Refresh Check Time
```

Create a Power Query named `RefreshCheck` using:

```powerquery
let
    RefreshTime = DateTime.FixedLocalNow(),
    Result = #table(
        type table [LastRefresh = datetime],
        {{RefreshTime}}
    )
in
    Result
```

Load the query and display `LastRefresh` as a date-time card.

A newer timestamp verifies that the check query ran again.
Together with refresh-dialog observation, it provides evidence
of a refresh cycle, not proof of success for every report table.

## Corrections

The Corrections window supports reviewed outer-whitespace removal
for selected text columns.

It creates a separate corrected workbook and audit record,
then checks the corrected workbook against the selected baseline.

It does not replace the incoming or approved workbook,
and it does not trigger Power BI refresh.

## Tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The existing automated tests cover structural comparison scenarios.
They do not cover the complete desktop automation workflow.

## Current limitations

- Portfolio prototype, not a production-ready general-purpose agent.
- First-row headers and tabular `.xlsx` files are assumed.
- Structural similarity does not guarantee business correctness.
- Formulas are not recalculated by openpyxl and require review.
- AI review and corrections are user-initiated, not autonomous
  stages of the monitoring pipeline.
- Power BI automation is specific to the tested desktop setup.
- Unknown refresh outcomes stop monitoring for manual review.
- The lock does not coordinate independent project copies or
  manual Power BI actions.
- Advanced Excel features may not survive library-based rewriting;
  use copies and verify outputs.

## Planned development

- More reliable and configurable Power BI targeting.
- Broader automated tests and compatibility checks.
- Reviewed AI-assisted rule onboarding.
- Policy-controlled corrections within the monitoring pipeline.
- Packaging and testing on additional Windows devices.