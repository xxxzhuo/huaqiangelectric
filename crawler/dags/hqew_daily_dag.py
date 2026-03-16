"""Airflow DAG placeholder for HQEW daily crawler workflow."""

from __future__ import annotations

from datetime import datetime


def build_dag_definition() -> dict:
    """Return lightweight DAG metadata without importing Airflow at runtime."""
    return {
        "dag_id": "hqew_daily_crawler",
        "schedule": "30 0 * * *",
        "start_date": datetime(2025, 1, 1).isoformat(),
        "tasks": ["discover", "crawl", "parse", "upsert", "diff", "report"],
    }


if __name__ == "__main__":
    print(build_dag_definition())
