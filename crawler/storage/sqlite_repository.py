from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from crawler.models.schemas import ChangeEvent, ProductRecord


class SQLiteProductRepository:
    def __init__(self, db_path: str = "crawler.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_current (
                    site_product_id TEXT PRIMARY KEY,
                    source_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'online',
                    brand TEXT,
                    model TEXT,
                    stock INTEGER,
                    price_min REAL,
                    price_max REAL,
                    seller_name TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_product_id TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    changed_fields_json TEXT NOT NULL,
                    captured_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS change_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_key TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    changed_fields_json TEXT NOT NULL,
                    at TEXT NOT NULL
                )
                """
            )

    def upsert(self, record: ProductRecord) -> None:
        payload = json.dumps(asdict(record), default=str, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO product_current (
                    site_product_id, source_url, title, status, brand, model,
                    stock, price_min, price_max, seller_name, payload_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_product_id) DO UPDATE SET
                    source_url=excluded.source_url,
                    title=excluded.title,
                    status=excluded.status,
                    brand=excluded.brand,
                    model=excluded.model,
                    stock=excluded.stock,
                    price_min=excluded.price_min,
                    price_max=excluded.price_max,
                    seller_name=excluded.seller_name,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    record.site_product_id,
                    record.source_url,
                    record.title,
                    record.status,
                    record.brand,
                    record.model,
                    record.stock,
                    record.price_min,
                    record.price_max,
                    record.seller_name,
                    payload,
                    record.last_seen_at.isoformat(),
                ),
            )

    def save_change(self, record: ProductRecord, event: ChangeEvent) -> None:
        snapshot = json.dumps(asdict(record), default=str, ensure_ascii=False)
        changed_fields_json = json.dumps(event.changed_fields, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO product_history (
                    site_product_id, snapshot_json, change_type, changed_fields_json, captured_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.site_product_id,
                    snapshot,
                    event.change_type,
                    changed_fields_json,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.execute(
                """
                INSERT INTO change_events (product_key, change_type, changed_fields_json, at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event.product_key,
                    event.change_type,
                    changed_fields_json,
                    event.at.isoformat(),
                ),
            )

    def get(self, site_product_id: str) -> ProductRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM product_current WHERE site_product_id = ?",
                (site_product_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        return ProductRecord(**payload)

    def list_current_product_ids(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT site_product_id FROM product_current WHERE status != 'delist'").fetchall()
        return [row[0] for row in rows]

    def mark_delisted(self, site_product_id: str) -> ChangeEvent | None:
        record = self.get(site_product_id)
        if record is None or record.status == "delist":
            return None

        record.status = "delist"
        record.last_seen_at = datetime.utcnow()
        event = ChangeEvent(product_key=site_product_id, change_type="delist", changed_fields=["status"])
        self.upsert(record)
        self.save_change(record, event)
        return event

    def list_changes(self, limit: int = 100) -> list[ChangeEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT product_key, change_type, changed_fields_json, at FROM change_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        events: list[ChangeEvent] = []
        for product_key, change_type, changed_fields_json, at in rows:
            events.append(
                ChangeEvent(
                    product_key=product_key,
                    change_type=change_type,
                    changed_fields=json.loads(changed_fields_json),
                    at=datetime.fromisoformat(at),
                )
            )
        return events
