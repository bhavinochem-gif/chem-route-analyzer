import sqlite3
import json
from datetime import datetime

DB_FILE = "chem_routes.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS synthesis_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                route_summary TEXT,
                reaction_names TEXT,
                total_steps INTEGER,
                full_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_route(file_hash: str, file_name: str, analysis_data: dict) -> int:
    summary = analysis_data.get("overall_route_summary", "No summary available")
    steps = analysis_data.get("steps", [])
    total_steps = len(steps)
    reaction_names = ", ".join([s.get("reaction_name", "Unknown") for s in steps])
    full_json_str = json.dumps(analysis_data)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO synthesis_routes (file_hash, file_name, route_summary, reaction_names, total_steps, full_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_hash) DO UPDATE SET
                file_name = excluded.file_name,
                route_summary = excluded.route_summary,
                reaction_names = excluded.reaction_names,
                total_steps = excluded.total_steps,
                full_json = excluded.full_json,
                created_at = excluded.created_at
        """, (file_hash, file_name, summary, reaction_names, total_steps, full_json_str, datetime.now()))
        conn.commit()
        return cursor.lastrowid

def get_route_by_hash(file_hash: str) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT full_json FROM synthesis_routes WHERE file_hash = ?", (file_hash,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["full_json"])
    return None

def get_all_routes() -> list[sqlite3.Row]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, file_name, route_summary, reaction_names, total_steps, created_at 
            FROM synthesis_routes 
            ORDER BY created_at DESC
        """)
        return cursor.fetchall()

def get_route_by_id(route_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT full_json FROM synthesis_routes WHERE id = ?", (route_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["full_json"])
    return None

def delete_route_by_id(route_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM synthesis_routes WHERE id = ?", (route_id,))
        conn.commit()
