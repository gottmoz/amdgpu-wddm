"""Transactional local state store for Strata task recovery."""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

SCHEMA_VERSION = 1
DDL = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, branch TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS checkpoints(task_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tool_calls(id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL, created_utc TEXT NOT NULL, UNIQUE(task_id,fingerprint));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS validations(task_id TEXT NOT NULL, result TEXT NOT NULL, created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_queue(task_id TEXT PRIMARY KEY, artifact TEXT NOT NULL, state TEXT NOT NULL, created_utc TEXT NOT NULL);
"""

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def connect(path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(p,timeout=30,isolation_level="IMMEDIATE")
    db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL"); db.executescript(DDL)
    db.execute("INSERT OR REPLACE INTO meta VALUES('schema_version',?)",(str(SCHEMA_VERSION),)); db.commit()
    return db

def upsert_task(db, task, state=None):
    with db:
        db.execute("INSERT INTO tasks VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET branch=excluded.branch,state=excluded.state,payload=excluded.payload,updated_utc=excluded.updated_utc",(task["id"],task.get("branch",""),state or task.get("status","pending"),json.dumps(task),now()))

def checkpoint(db, task_id, payload):
    with db: db.execute("INSERT OR REPLACE INTO checkpoints VALUES(?,?,?)",(task_id,json.dumps(payload),now()))

def recover_running(db):
    with db:
        rows=db.execute("SELECT id,payload FROM tasks WHERE state='running'").fetchall()
        for task_id,payload in rows: db.execute("UPDATE tasks SET state='retry_scheduled',updated_utc=? WHERE id=?",(now(),task_id))
    return [x[0] for x in rows]
