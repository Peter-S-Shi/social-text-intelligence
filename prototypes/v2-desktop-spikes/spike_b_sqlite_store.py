"""PROTOTYPE (throwaway) - Spike B: persistence boundary (SQLite, per-user app data).

Questions:
  1. Can the per-user data directory be resolved without a new dependency?
  2. Does the schema keep AI predictions and human judgments separate (V1 rule)?
  3. Is "delete" real: after delete, is the text still recoverable from the file bytes?
  4. Do two connections (UI thread + worker) coexist, and does an interrupted write
     leave the DB consistent?

Run: python spike_b_sqlite_store.py   (writes only to a scratch dir, then wipes it)
"""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from ctypes import wintypes
from pathlib import Path

APP_DIR_NAME = "SocialTextIntelligence"
SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE project (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_utc TEXT NOT NULL,
  retention_days INTEGER            -- NULL = keep until explicitly deleted
);
CREATE TABLE record (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL
    REFERENCES project(id) ON DELETE CASCADE,
  row_number INTEGER, text TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}'
);
-- immutable AI output, one row per (record, run); never updated after insert
CREATE TABLE analysis (
  id TEXT PRIMARY KEY, record_id TEXT NOT NULL
    REFERENCES record(id) ON DELETE CASCADE,
  created_utc TEXT NOT NULL, model_revisions_json TEXT NOT NULL,
  report_json TEXT NOT NULL
);
-- separate human judgment; first decision immutable, later ones are revisions
CREATE TABLE human_review (
  id TEXT PRIMARY KEY, record_id TEXT NOT NULL
    REFERENCES record(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL, created_utc TEXT NOT NULL, judgment_json TEXT NOT NULL,
  UNIQUE (record_id, revision)
);
"""


def user_data_dir() -> Path:
    """%LOCALAPPDATA%\\SocialTextIntelligence via the Known Folder API (no deps)."""

    override = os.environ.get("STI_SPIKE_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform != "win32":
        return Path.home() / ".local" / "share" / APP_DIR_NAME
    guid = (ctypes.c_byte * 16)()
    # FOLDERID_LocalAppData = {F1B32785-6FBA-4FCF-9D55-7B8E7F157091}
    ctypes.oledll.ole32.CLSIDFromString("{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}", guid)
    out = ctypes.c_wchar_p()
    shget = ctypes.windll.shell32.SHGetKnownFolderPath
    shget.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE,
                      ctypes.POINTER(ctypes.c_wchar_p)]
    shget(ctypes.byref(guid), 0, None, ctypes.byref(out))
    path = Path(out.value or "") / APP_DIR_NAME
    ctypes.windll.ole32.CoTaskMemFree(out)
    return path


def open_db(path: Path, *, secure_delete: bool = True) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, isolation_level=None, timeout=5)
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(f"PRAGMA secure_delete={'ON' if secure_delete else 'OFF'}")
    if con.execute("PRAGMA user_version").fetchone()[0] == 0:
        con.executescript(SCHEMA)
        con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    return con


def add_project_with_record(con: sqlite3.Connection, text: str) -> tuple[str, str]:
    pid, rid = uuid.uuid4().hex, uuid.uuid4().hex
    con.execute("BEGIN IMMEDIATE")
    con.execute("INSERT INTO project VALUES (?,?,?,?)",
                (pid, "demo", "2026-10-06T00:00:00Z", 30))
    con.execute("INSERT INTO record VALUES (?,?,?,?,?)", (rid, pid, 1, text, "{}"))
    con.execute("INSERT INTO analysis VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex, rid, "2026-10-06T00:00:01Z", "{}",
                 json.dumps({"sentiment": "positive", "echo": text})))
    con.execute("INSERT INTO human_review VALUES (?,?,?,?,?)",
                (uuid.uuid4().hex, rid, 1, "2026-10-06T00:00:02Z",
                 json.dumps({"judgment": "accept", "note": text})))
    con.execute("COMMIT")
    return pid, rid


def file_contains(db: Path, needle: bytes) -> bool:
    for suffix in ("", "-wal", "-shm"):
        part = Path(str(db) + suffix)
        if part.exists() and needle in part.read_bytes():
            return True
    return False


def export_project(con: sqlite3.Connection, pid: str) -> dict[str, object]:
    rows = con.execute(
        "SELECT r.text, a.report_json, h.judgment_json FROM record r "
        "LEFT JOIN analysis a ON a.record_id=r.id "
        "LEFT JOIN human_review h ON h.record_id=r.id WHERE r.project_id=?", (pid,)
    ).fetchall()
    return {"project": pid, "rows": rows}


def purge_expired(con: sqlite3.Connection, now_utc: str) -> int:
    cur = con.execute(
        "DELETE FROM project WHERE retention_days IS NOT NULL AND "
        "julianday(?) - julianday(created_utc) > retention_days", (now_utc,))
    return cur.rowcount


def main() -> int:
    results: dict[str, object] = {}
    real_dir = user_data_dir()
    results["resolved_user_data_dir_is_under_localappdata"] = (
        os.environ.get("LOCALAPPDATA", "?").lower() in str(real_dir).lower()
        if sys.platform == "win32" else "n/a"
    )
    results["resolved_dir_name"] = real_dir.name  # not the full path (privacy)

    scratch = Path(tempfile.mkdtemp(prefix="sti-spike-b-WIPE-ME-"))
    try:
        # --- delete is real? compare secure_delete ON vs OFF, with VACUUM -------
        for flag in (False, True):
            db = scratch / f"t_{flag}.db"
            con = open_db(db, secure_delete=flag)
            needle = ("ZQXJ-secret-" + uuid.uuid4().hex).encode()
            pid, _ = add_project_with_record(con, needle.decode())
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            before = file_contains(db, needle)
            con.execute("DELETE FROM project WHERE id=?", (pid,))
            con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            after_delete = file_contains(db, needle)
            con.execute("VACUUM")
            after_vacuum = file_contains(db, needle)
            cascades = con.execute("SELECT count(*) FROM record").fetchone()[0]
            con.close()
            results[f"secure_delete={flag}"] = {
                "text_in_file_before": before,
                "text_recoverable_after_delete": after_delete,
                "text_recoverable_after_vacuum": after_vacuum,
                "cascade_left_records": cascades,
            }

        # --- two connections: UI reader + worker writer ------------------------
        db = scratch / "multi.db"
        writer, reader = open_db(db), open_db(db)
        pid, _ = add_project_with_record(writer, "hello")
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE project SET name='mid-write' WHERE id=?", (pid,))
        seen_during = reader.execute("SELECT name FROM project").fetchone()[0]
        writer.execute("COMMIT")
        results["reader_sees_committed_state_during_write"] = seen_during == "demo"
        results["reader_sees_new_state_after_commit"] = (
            reader.execute("SELECT name FROM project").fetchone()[0] == "mid-write")

        # --- interrupted write: kill a child mid-transaction -------------------
        db2 = scratch / "crash.db"
        crash_con = open_db(db2)
        add_project_with_record(crash_con, "committed-before-crash")
        crash_con.close()
        child = (
            "import sqlite3,os,sys;"
            f"c=sqlite3.connect(r'{db2}',isolation_level=None);"
            "c.execute('PRAGMA journal_mode=WAL');c.execute('BEGIN IMMEDIATE');"
            "c.execute(\"INSERT INTO project VALUES ('half','half','x',NULL)\");"
            "print('mid',flush=True);os._exit(9)"
        )
        subprocess.run([sys.executable, "-c", child], capture_output=True, timeout=20)
        after_crash = open_db(db2)
        n = after_crash.execute("SELECT count(*) FROM project").fetchone()[0]
        ok = after_crash.execute("PRAGMA integrity_check").fetchone()[0]
        results["after_killed_mid_transaction"] = {"projects": n, "integrity": ok}
        after_crash.close()

        # --- retention + export ------------------------------------------------
        db3 = scratch / "ret.db"
        c3 = open_db(db3)
        pid3, _ = add_project_with_record(c3, "retention text")
        results["export_rows"] = len(export_project(c3, pid3)["rows"])
        results["purged_when_expired"] = purge_expired(c3, "2026-12-31T00:00:00Z")
        results["records_left_after_purge"] = c3.execute(
            "SELECT count(*) FROM record").fetchone()[0]
        c3.close()
        results["sqlite_version"] = sqlite3.sqlite_version
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
