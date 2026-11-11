import argparse
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import duckdb


API = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
REPORT = Path(__file__).with_name("report.sql")


def fetch_requests(start: date, end: date, limit: int) -> list[dict]:
    query = urlencode({
        "$select": "unique_key,created_date,closed_date,complaint_type",
        "$where": f"created_date >= '{start}T00:00:00' AND created_date < '{end}T00:00:00'",
        "$order": "created_date ASC,unique_key ASC",
        "$limit": limit,
    })
    with urlopen(f"{API}?{query}", timeout=30) as response:
        return json.load(response)


def normalize(records: list[dict]) -> list[tuple]:
    rows = []
    seen = set()
    for record in records:
        key = record["unique_key"].strip()
        problem = record["complaint_type"].strip()
        created = datetime.fromisoformat(record["created_date"])
        closed_value = record.get("closed_date")
        closed = datetime.fromisoformat(closed_value) if closed_value else None
        if not key or not problem or key in seen:
            raise ValueError("Input contains a missing key, missing problem, or duplicate key.")
        if created.tzinfo or (closed and (closed.tzinfo or closed < created)):
            raise ValueError(f"Unexpected dates for request {key}.")
        seen.add(key)
        rows.append((key, created, closed, problem))
    return rows


def load_requests(database: Path, records: list[dict]) -> dict:
    rows = normalize(records)
    with duckdb.connect(str(database)) as db:
        db.execute("BEGIN TRANSACTION")
        db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id VARCHAR PRIMARY KEY,
                created_at TIMESTAMP NOT NULL,
                closed_at TIMESTAMP,
                complaint_type VARCHAR NOT NULL
            )
        """)
        db.execute("CREATE TEMP TABLE incoming AS SELECT * FROM requests WHERE FALSE")
        if rows:
            db.executemany("INSERT INTO incoming VALUES (?, ?, ?, ?)", rows)
        inserted, updated = db.execute("""
            SELECT count(*) FILTER (WHERE stored.request_id IS NULL),
                   count(*) FILTER (
                       WHERE stored.request_id IS NOT NULL AND (
                           stored.created_at IS DISTINCT FROM incoming.created_at OR
                           stored.closed_at IS DISTINCT FROM incoming.closed_at OR
                           stored.complaint_type IS DISTINCT FROM incoming.complaint_type
                       )
                   )
            FROM incoming LEFT JOIN requests AS stored USING (request_id)
        """).fetchone()
        db.execute("""
            INSERT INTO requests SELECT * FROM incoming
            ON CONFLICT (request_id) DO UPDATE SET
                created_at = excluded.created_at,
                closed_at = excluded.closed_at,
                complaint_type = excluded.complaint_type
            WHERE requests.created_at IS DISTINCT FROM excluded.created_at
               OR requests.closed_at IS DISTINCT FROM excluded.closed_at
               OR requests.complaint_type IS DISTINCT FROM excluded.complaint_type
        """)
        report = db.execute(REPORT.read_text(encoding="utf-8"))
        columns = [column[0] for column in report.description]
        summary = [dict(zip(columns, row)) for row in report.fetchall()]
        db.execute("COMMIT")
    return {
        "input": len(rows), "inserted": inserted, "updated": updated,
        "unchanged": len(rows) - inserted - updated, "by_problem": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and summarize NYC 311 requests.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Local JSON array in NYC Open Data format")
    source.add_argument("--start", type=date.fromisoformat, help="Inclusive creation date")
    parser.add_argument("--end", type=date.fromisoformat, help="Exclusive creation date")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum live requests, 1–5000")
    parser.add_argument("--db", type=Path, default=Path("requests.duckdb"))
    args = parser.parse_args()
    if args.start and (not args.end or args.end <= args.start or not 1 <= args.limit <= 5000):
        parser.error("Live mode requires an end date after the start and a limit from 1 to 5000.")
    records = (
        json.loads(args.input.read_text(encoding="utf-8"))
        if args.input else fetch_requests(args.start, args.end, args.limit)
    )
    print(json.dumps(load_requests(args.db, records), indent=2))


if __name__ == "__main__":
    main()
