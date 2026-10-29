"""Comptes utilisateurs : inscription, connexion, sessions.

- Mots de passe hachés avec PBKDF2-HMAC-SHA256 (sel aléatoire, 200 000 itérations), jamais stockés en clair.
- Session : jeton aléatoire envoyé dans un cookie HttpOnly ; seule son empreinte SHA-256 est stockée en base.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from .db import Database

STARTING_CASH = 100_000.0
SESSION_DAYS = 30
PBKDF2_ITERATIONS = 200_000

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[A-Za-z]{2,}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,20}$")


class AuthError(ValueError):
    """Erreur d'authentification (message affichable à l'utilisateur)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return digest.hex(), salt


def verify_password(password: str, pw_hash: str, salt: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt)[0], pw_hash)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- limitation des tentatives de connexion (en mémoire) ----------
_ATTEMPTS: dict[str, deque] = defaultdict(deque)
MAX_ATTEMPTS, WINDOW = 10, 600  # 10 essais par 10 minutes


def check_rate_limit(key: str) -> None:
    now = time.time()
    q = _ATTEMPTS[key]
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= MAX_ATTEMPTS:
        raise AuthError("Trop de tentatives. Réessaie dans quelques minutes.")
    q.append(now)


# ---------- opérations ----------
def register(db: Database, email: str, username: str, password: str) -> dict:
    email = email.strip().lower()
    username = username.strip()
    if not EMAIL_RE.match(email):
        raise AuthError("Adresse email invalide.")
    if not USERNAME_RE.match(username):
        raise AuthError("Pseudo invalide : 3 à 20 caractères (lettres, chiffres, _ ou -).")
    if len(password) < 8:
        raise AuthError("Le mot de passe doit faire au moins 8 caractères.")
    if len(password) > 200:
        raise AuthError("Mot de passe trop long.")
    pw_hash, salt = hash_password(password)
    with db.transaction() as cur:
        if cur.execute("SELECT 1 AS x FROM users WHERE email = ?", (email,)).one():
            raise AuthError("Un compte existe déjà avec cet email.")
        if cur.execute("SELECT 1 AS x FROM users WHERE LOWER(username) = LOWER(?)", (username,)).one():
            raise AuthError("Ce pseudo est déjà pris.")
        uid = cur.insert(
            "INSERT INTO users (email, username, pw_hash, pw_salt, cash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (email, username, pw_hash, salt, STARTING_CASH, _now().isoformat()),
        )
    return {"id": uid, "email": email, "username": username}


def login(db: Database, email: str, password: str) -> tuple[dict, str]:
    """Vérifie les identifiants et crée une session. Renvoie (utilisateur, jeton)."""
    email = email.strip().lower()
    with db.transaction() as cur:
        user = cur.execute("SELECT * FROM users WHERE email = ?", (email,)).one()
    if not user or not verify_password(password, user["pw_hash"], user["pw_salt"]):
        raise AuthError("Email ou mot de passe incorrect.")
    return _public(user), create_session(db, user["id"])


def create_session(db: Database, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (_now() + timedelta(days=SESSION_DAYS)).isoformat()
    with db.transaction() as cur:
        cur.execute("DELETE FROM sessions WHERE expires_at < ?", (_now().isoformat(),))
        cur.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                    (_token_hash(token), user_id, expires))
    return token


def user_from_token(db: Database, token: str | None) -> dict | None:
    if not token:
        return None
    with db.transaction() as cur:
        row = cur.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (_token_hash(token), _now().isoformat()),
        ).one()
    return _public(row) if row else None


def logout(db: Database, token: str | None) -> None:
    if token:
        with db.transaction() as cur:
            cur.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def _public(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "username": user["username"]}
