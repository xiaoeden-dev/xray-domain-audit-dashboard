from __future__ import annotations

import asyncio
import gzip
import hashlib
import hmac
import ipaddress
import logging
import os
import re
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
LOG_DIR = Path(os.getenv("XRAY_LOG_DIR", "/var/log/x-ui"))
ACTIVE_LOG = LOG_DIR / "access.log"
DB_PATH = Path(os.getenv("XRAY_DASHBOARD_DB", "/var/lib/xray-dashboard/history.sqlite3"))
LOGIN_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
SESSION_COOKIE = "xraydash_session"
SESSION_MAX_AGE = 12 * 60 * 60
POLL_SECONDS = 1.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s xray-dashboard: %(message)s",
)
logger = logging.getLogger("xray-dashboard")

TIMESTAMP_RE = re.compile(r"^(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2}(?:\.\d+)?)")
ACCEPTED_RE = re.compile(r"\baccepted\s+(tcp|udp):")
EMAIL_RE = re.compile(r"\bemail:\s*([^\s]+)")
INBOUND_RE = re.compile(r"\[([^\]]*>>[^\]]*)\]")
VALID_DOMAIN_RE = re.compile(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}\Z")


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 20000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def db_session():
    conn = connect_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db_session() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                client TEXT NOT NULL,
                domain TEXT,
                destination TEXT NOT NULL,
                destination_kind TEXT NOT NULL,
                protocol TEXT NOT NULL,
                port INTEGER,
                inbound TEXT,
                fingerprint TEXT NOT NULL UNIQUE
            );
            CREATE INDEX IF NOT EXISTS idx_events_client_time ON events(client, timestamp_utc DESC);
            CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp_utc DESC);
            CREATE INDEX IF NOT EXISTS idx_events_domain ON events(domain);
            CREATE TABLE IF NOT EXISTS collector_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS imported_files (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL
            );
            """
        )


def get_state(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM collector_state WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else None


def set_state(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO collector_state(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def parse_access_line(raw_line: str) -> dict[str, Any] | None:
    """Extract only connection metadata; deliberately discard source IPs and raw lines."""
    timestamp_match = TIMESTAMP_RE.match(raw_line)
    accepted_match = ACCEPTED_RE.search(raw_line)
    email_match = EMAIL_RE.search(raw_line)
    if not (timestamp_match and accepted_match and email_match):
        return None

    try:
        parsed_time = datetime.fromisoformat(
            timestamp_match.group(1).replace("/", "-") + "T" + timestamp_match.group(2)
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    protocol = accepted_match.group(1).lower()
    remainder = raw_line[accepted_match.end():]
    # Xray places the inbound/routing tag after the destination, e.g. [in-22872-tcp >> direct].
    destination = remainder.split(" [", 1)[0].strip()
    if not destination:
        return None

    host = destination
    port: int | None = None
    host_part, separator, port_part = destination.rpartition(":")
    if separator and port_part.isdigit():
        host = host_part.strip()
        port = int(port_part)

    # Xray's maskAddress output can contain spaces, e.g. [Masked IPv4]. Keep it as an
    # unavailable destination rather than accidentally treating part of it as a domain.
    clean_host = host.strip()
    unwrapped_host = clean_host[1:-1] if clean_host.startswith("[") and clean_host.endswith("]") else clean_host
    destination_kind = "unknown"
    domain: str | None = None
    try:
        ipaddress.ip_address(unwrapped_host)
        destination_kind = "ip"
    except ValueError:
        if "masked" in unwrapped_host.lower() or "[" in unwrapped_host or "]" in unwrapped_host:
            destination_kind = "masked"
        elif VALID_DOMAIN_RE.fullmatch(unwrapped_host):
            destination_kind = "domain"
            domain = unwrapped_host.lower().rstrip(".")
        else:
            destination_kind = "unknown"

    inbound_match = INBOUND_RE.search(raw_line)
    inbound = inbound_match.group(1).strip() if inbound_match else None
    client = email_match.group(1).strip()
    fingerprint = hashlib.sha256(raw_line.rstrip("\r\n").encode("utf-8", "replace")).hexdigest()

    return {
        "timestamp_utc": parsed_time.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "client": client,
        "domain": domain,
        "destination": clean_host,
        "destination_kind": destination_kind,
        "protocol": protocol,
        "port": port,
        "inbound": inbound,
        "fingerprint": fingerprint,
    }


def insert_line(conn: sqlite3.Connection, raw_line: str) -> bool:
    event = parse_access_line(raw_line)
    if event is None:
        return False
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO events
        (timestamp_utc, client, domain, destination, destination_kind, protocol, port, inbound, fingerprint)
        VALUES (:timestamp_utc, :client, :domain, :destination, :destination_kind, :protocol, :port, :inbound, :fingerprint)
        """,
        event,
    )
    return cursor.rowcount > 0


def open_log_text(path: Path):
    if path.name.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("rt", encoding="utf-8", errors="replace")


def import_archives() -> None:
    if not LOG_DIR.is_dir():
        logger.warning("Xray log directory is unavailable: %s", LOG_DIR)
        return
    files = sorted(p for p in LOG_DIR.glob("access.log-*") if p.is_file())
    for path in files:
        try:
            stat = path.stat()
            with db_session() as conn:
                previous = conn.execute(
                    "SELECT size, mtime_ns FROM imported_files WHERE path = ?", (str(path),)
                ).fetchone()
                if previous and previous["size"] == stat.st_size and previous["mtime_ns"] == stat.st_mtime_ns:
                    continue
                added = 0
                with open_log_text(path) as source:
                    for line in source:
                        if insert_line(conn, line):
                            added += 1
                conn.execute(
                    "INSERT INTO imported_files(path, size, mtime_ns) VALUES(?, ?, ?) "
                    "ON CONFLICT(path) DO UPDATE SET size=excluded.size, mtime_ns=excluded.mtime_ns",
                    (str(path), stat.st_size, stat.st_mtime_ns),
                )
            logger.info("Imported archive %s (%d new events)", path.name, added)
        except (OSError, EOFError, gzip.BadGzipFile) as exc:
            logger.warning("Could not import archive %s: %s", path.name, exc)


def ingest_active_log(rescan: bool = False) -> None:
    try:
        stat = ACTIVE_LOG.stat()
    except FileNotFoundError:
        return

    with db_session() as conn:
        old_inode = get_state(conn, "active_inode")
        old_offset_text = get_state(conn, "active_offset")
        offset = 0 if rescan else int(old_offset_text or "0")
        if rescan or old_inode != str(stat.st_ino) or stat.st_size < offset:
            offset = 0

        try:
            with ACTIVE_LOG.open("rb") as source:
                source.seek(offset)
                data = source.read()
        except OSError as exc:
            logger.warning("Could not read active access log: %s", exc)
            return

        # Only commit complete lines; a partially written final line is picked up next poll.
        last_newline = data.rfind(b"\n")
        if last_newline < 0:
            set_state(conn, "active_inode", str(stat.st_ino))
            set_state(conn, "active_offset", str(offset))
            return

        complete_data = data[: last_newline + 1]
        added = 0
        for raw in complete_data.splitlines():
            line = raw.decode("utf-8", "replace")
            if insert_line(conn, line):
                added += 1

        new_offset = offset + last_newline + 1
        set_state(conn, "active_inode", str(stat.st_ino))
        set_state(conn, "active_offset", str(new_offset))
        if added:
            logger.info("Collected %d new connection events", added)


async def collector_loop() -> None:
    # Import existing archives and recover the active file on startup.
    await asyncio.to_thread(import_archives)
    await asyncio.to_thread(ingest_active_log, True)

    # Recheck archives periodically to capture newly rotated access logs.
    archive_scan_interval = 30.0
    next_archive_scan = time.monotonic() + archive_scan_interval

    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            await asyncio.to_thread(ingest_active_log)
            if time.monotonic() >= next_archive_scan:
                await asyncio.to_thread(import_archives)
                next_archive_scan = time.monotonic() + archive_scan_interval
        except Exception:
            logger.exception("Collector pass failed; it will retry")


def make_session_signature(timestamp: str) -> str:
    message = f"{timestamp}:xray-dashboard".encode()
    return hmac.new(SESSION_SECRET.encode(), message, hashlib.sha256).hexdigest()


def has_valid_session(request: Request) -> bool:
    token = request.cookies.get(SESSION_COOKIE, "")
    try:
        timestamp, signature = token.split(":", 1)
        issued = int(timestamp)
    except (ValueError, TypeError):
        return False
    now = int(time.time())
    if issued > now + 60 or now - issued > SESSION_MAX_AGE:
        return False
    expected = make_session_signature(timestamp)
    return hmac.compare_digest(signature, expected)


login_attempts: dict[str, list[float]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not LOGIN_PASSWORD or not SESSION_SECRET:
        raise RuntimeError("DASHBOARD_PASSWORD and SESSION_SECRET must be set in the service environment")
    if not ACTIVE_LOG.exists():
        logger.warning("Active Xray access log does not exist yet: %s", ACTIVE_LOG)
    init_db()
    collector_task = asyncio.create_task(collector_loop())
    yield
    collector_task.cancel()
    try:
        await collector_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Xray Monitor", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/session")
async def session_status(request: Request):
    return {"authenticated": has_valid_session(request)}


@app.post("/api/login")
async def login(request: Request, response: Response):
    origin = request.headers.get("origin")
    host_header = request.headers.get("host", "")
    if origin:
        from urllib.parse import urlparse
        if urlparse(origin).netloc != host_header:
            raise HTTPException(status_code=403, detail="Invalid request origin")

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = [t for t in login_attempts.get(client_ip, []) if now - t < 600]
    if len(attempts) >= 5:
        login_attempts[client_ip] = attempts
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 10 minutes.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request")
    supplied = str(payload.get("password", "")) if isinstance(payload, dict) else ""
    if not hmac.compare_digest(supplied, LOGIN_PASSWORD):
        attempts.append(now)
        login_attempts[client_ip] = attempts
        raise HTTPException(status_code=401, detail="Incorrect password")

    login_attempts.pop(client_ip, None)
    timestamp = str(int(now))
    token = f"{timestamp}:{make_session_signature(timestamp)}"
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=False,  # The app is reachable only over the encrypted Tailscale interface.
        samesite="strict",
        path="/",
    )
    return {"ok": True}


@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="strict")
    return {"ok": True}


def require_auth(request: Request) -> None:
    if not has_valid_session(request):
        raise HTTPException(status_code=401, detail="Please sign in")


@app.get("/api/clients")
async def clients(request: Request):
    require_auth(request)
    with db_session() as conn:
        rows = conn.execute(
            "SELECT client, COUNT(*) AS event_count, MAX(timestamp_utc) AS last_seen "
            "FROM events GROUP BY client ORDER BY last_seen DESC, client COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/stats")
async def stats(request: Request):
    require_auth(request)
    with db_session() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, COUNT(DISTINCT client) AS clients, "
            "SUM(CASE WHEN domain IS NOT NULL THEN 1 ELSE 0 END) AS identified "
            "FROM events"
        ).fetchone()
    return dict(row)


@app.get("/api/events")
async def events(
    request: Request,
    client: str = "",
    q: str = "",
    from_utc: str = "",
    to_utc: str = "",
    limit: int = 50,
    offset: int = 0,
):
    require_auth(request)
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    clauses: list[str] = []
    params: list[Any] = []
    if client and client != "__all__":
        clauses.append("client = ?")
        params.append(client)
    if q:
        clauses.append("(domain LIKE ? ESCAPE '\\' OR destination LIKE ? ESCAPE '\\')")
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    if from_utc:
        clauses.append("timestamp_utc >= ?")
        params.append(from_utc)
    if to_utc:
        clauses.append("timestamp_utc < ?")
        params.append(to_utc)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""

    with db_session() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM events{where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, timestamp_utc, client, domain, destination, destination_kind, protocol, port, inbound "
            f"FROM events{where} ORDER BY timestamp_utc DESC, id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    return {"total": total, "items": [dict(row) for row in rows], "limit": limit, "offset": offset}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
