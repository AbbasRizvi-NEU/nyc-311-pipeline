# NYC 311 Pipeline

City service requests can close after they first appear in a dataset. This Python and DuckDB project loads a slice of NYC 311 data, updates stored requests by ID, and reports median hours to close by problem type.

## Run the demo

Use Python 3.12 and run these commands in PowerShell from the repository root.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe pipeline.py --input demo.json --db demo.duckdb
.\.venv\Scripts\python.exe pipeline.py --input demo.json --db demo.duckdb
.\.venv\Scripts\python.exe pipeline.py --input demo-update.json --db demo.duckdb
```

On a fresh database, the first run inserts three fictional requests. The second inserts zero and reports three unchanged. The third updates one existing request and moves the median from 4 to 6 hours. The report includes every request in the chosen database and calculates the median using closed requests only.

## Try live data

```powershell
.\.venv\Scripts\python.exe pipeline.py --start 2025-01-01 --end 2025-02-01 --limit 100 --db requests.duckdb
```

The pipeline fetches a bounded slice ordered by creation time and request ID. The command above retrieves up to 100 records from January. Its report describes that slice, which is useful for testing the load and inspecting the output. NYC stores local timestamps without an offset, so the report uses the timestamps as provided. The data source is [NYC Open Data's 311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9). Only request ID, timestamps, and problem type are fetched.

Run `python -m unittest -v` in the environment to verify the repeat load, update, and invalid batch behavior. The upsert and report run in one transaction. Duplicate IDs within a source batch or a closure time earlier than creation cause the batch to fail.

Portfolio project by [AbbasRizvi-NEU](https://github.com/AbbasRizvi-NEU), built with Codex assistance. [DuckDB](https://github.com/duckdb/duckdb/blob/main/LICENSE) is installed separately under the MIT license. The demo data is fictional.
