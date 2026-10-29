"""Accès base de données minimaliste : SQLite en local et dans les tests, PostgreSQL en production.

Les requêtes s'écrivent avec des « ? » ; ils sont convertis en « %s » pour PostgreSQL.
Variable d'environnement : DATABASE_URL (ex. postgresql://user:mdp@hote/base?sslmode=require).
Sans DATABASE_URL, on utilise le fichier local backend/optionlab.db.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id {PK},
    email TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    pw_hash TEXT NOT NULL,
    pw_salt TEXT NOT NULL,
    cash {FLOAT} NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    id {PK},
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    side TEXT NOT NULL,
    strike {FLOAT} NOT NULL,
    expiry TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price {FLOAT} NOT NULL,
    entry_spot {FLOAT} NOT NULL,
    last_spot {FLOAT} NOT NULL,
    last_vol {FLOAT} NOT NULL,
    last_q {FLOAT} NOT NULL,
    status TEXT NOT NULL,
    exit_price {FLOAT},
    realized_pnl {FLOAT},
    opened_at TEXT NOT NULL,
    closed_at TEXT
);
CREATE TABLE IF NOT EXISTS trades (
    id {PK},
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    description TEXT NOT NULL,
    price {FLOAT} NOT NULL,
    quantity INTEGER NOT NULL,
    cash_flow {FLOAT} NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id);
"""


class Database:
    def __init__(self, url: str | None = None):
        url = url if url is not None else os.environ.get("DATABASE_URL", "")
        if url.startswith(("postgres://", "postgresql://")):
            self.kind = "postgres"
            self.url = url.replace("postgres://", "postgresql://", 1)
        else:
            self.kind = "sqlite"
            path = url.removeprefix("sqlite:///") if url else str(Path(__file__).resolve().parents[1] / "optionlab.db")
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._lock = threading.Lock()

    # ---------- connexions ----------
    @contextmanager
    def transaction(self):
        """Ouvre une transaction ; commit à la sortie, rollback en cas d'erreur."""
        if self.kind == "sqlite":
            with self._lock:
                cur = self._conn.cursor()
                try:
                    yield _Cursor(cur, self.kind)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise
        else:
            import psycopg
            from psycopg.rows import dict_row
            with psycopg.connect(self.url, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    yield _Cursor(cur, self.kind)
                # psycopg commit automatiquement à la sortie du bloc sans erreur

    def init_schema(self) -> None:
        ddl = SCHEMA.format(
            PK="INTEGER PRIMARY KEY AUTOINCREMENT" if self.kind == "sqlite" else "SERIAL PRIMARY KEY",
            FLOAT="REAL" if self.kind == "sqlite" else "DOUBLE PRECISION",
        )
        with self.transaction() as cur:
            for stmt in filter(str.strip, ddl.split(";")):
                cur.execute(stmt)


class _Cursor:
    """Petit adaptateur : « ? » -> « %s » pour PostgreSQL, lignes renvoyées en dict."""

    def __init__(self, cur, kind: str):
        self._cur, self._kind = cur, kind

    def execute(self, sql: str, params: tuple = ()) -> "_Cursor":
        if self._kind == "postgres":
            sql = sql.replace("?", "%s")
        self._cur.execute(sql, params)
        return self

    def one(self) -> dict | None:
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def all(self) -> list[dict]:
        return [dict(r) for r in self._cur.fetchall()]

    def insert(self, sql: str, params: tuple = ()) -> int:
        """INSERT ... et renvoie l'id créé (RETURNING id fonctionne sur SQLite ≥ 3.35 et PostgreSQL)."""
        return self.execute(sql + " RETURNING id", params).one()["id"]

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def lock_user(self, user_id: int) -> dict | None:
        """Lit la ligne utilisateur en la verrouillant jusqu'à la fin de la transaction (PostgreSQL)."""
        suffix = " FOR UPDATE" if self._kind == "postgres" else ""
        return self.execute("SELECT * FROM users WHERE id = ?" + suffix, (user_id,)).one()
