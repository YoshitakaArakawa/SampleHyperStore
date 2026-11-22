"""OAuth (PKCE) sign-in helper for the SampleHyperStore setup scripts.

No token is stored in files you edit: the sign-in happens in your browser and the
session is cached outside the repository
(%LOCALAPPDATA%/samplehyperstore on Windows, ~/.config/samplehyperstore elsewhere).

Origin: forked from scripts/tableau_auth.py in tableau-datasource-steward (MIT,
same author) at commit 3f98ef7 (20261122). This file is maintained independently
and is the reference version for the SampleHyperStore setup; it is not kept in
sync with the steward plugin, which has its own copy for its own use. Intended
differences from the steward version:
  - reads only setup/.env (the steward version searches the working directory
    and its parents), with a small built-in reader instead of python-dotenv
  - callback port 8799 and cache folder "samplehyperstore", so it does not share
    a sign-in with the steward plugin
  - runs with pip and requirements.txt; no Claude Code, plugin or uv needed
  - the "state mismatch" error does not echo the state values
When fixing a bug in the OAuth flow here, check whether the steward version has
the same bug, and the other way round.

Reads setup/.env, runs OAuth 2.0
Authorization Code + PKCE flow against Tableau Cloud, injects the
resulting access_token into a tableauserverclient Server instance,
and yields it as a context manager.

Required .env variables: SERVER, SITE_NAME
Optional .env variables: OAUTH_CALLBACK_PORT (default 8799)

Usage:

    from tableau_auth import signed_in_server
    with signed_in_server() as server:
        for flow in TSC.Pager(server.flows):
            ...
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path

try:
    import tableauserverclient as TSC
except ImportError:
    sys.exit("ERROR: tableauserverclient is required. Install with: pip install -r requirements.txt")


CLIENT_TYPE = "samplehyperstore-setup"
USER_AGENT = "samplehyperstore-setup/0.1 (python)"
DEFAULT_CALLBACK_PORT = 8799
OAUTH_TIMEOUT_SECONDS = 300


ENV_FILE = Path(__file__).resolve().parent.parent / ".env"   # setup/.env only, never a parent folder's


def load_env_file(path: Path) -> None:
    """Minimal KEY=VALUE reader (no python-dotenv). Existing environment variables win."""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def load_credentials() -> dict:
    if ENV_FILE.exists():
        load_env_file(ENV_FILE)
        print(f"[auth] Loaded .env from: {ENV_FILE}", file=sys.stderr)
    else:
        print(f"[auth] WARNING: {ENV_FILE} not found. Relying on environment only.", file=sys.stderr)

    server_url = (os.environ.get("SERVER") or "").rstrip("/")
    if not server_url:
        sys.exit("ERROR: Missing required env var: SERVER")

    return {
        "server_url": server_url,
        "site_name":  os.environ.get("SITE_NAME", ""),
        "port":       int(os.environ.get("OAUTH_CALLBACK_PORT", DEFAULT_CALLBACK_PORT)),
    }


# ----- PKCE -----
def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


# ----- Local callback listener -----
class _CallbackResult:
    def __init__(self):
        self.code: str | None = None
        self.error: str | None = None
        self.event = threading.Event()


def _make_callback_handler(expected_state: str, result: _CallbackResult):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/Callback":
                self.send_response(404)
                self.end_headers()
                return
            query = urllib.parse.parse_qs(parsed.query)
            received_state = (query.get("state") or [None])[0]
            if received_state != expected_state:
                result.error = "state mismatch"
            else:
                result.code = (query.get("code") or [None])[0]
                if "error" in query:
                    result.error = (query.get("error") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>OAuth callback received.</h2>"
                b"<p>You can close this tab and return to your terminal.</p></body></html>"
            )
            result.event.set()

        def log_message(self, *_args, **_kwargs):
            return

    return Handler


# ----- raw HTTP helpers (stdlib only) -----
def _http_post_form(url: str, body: dict[str, str], timeout: int = 30) -> dict:
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise SystemExit(f"[auth] ERROR: POST {url} -> HTTP {e.code}\nbody: {body_text}")


def _http_get_json(url: str, headers: dict[str, str], timeout: int = 30) -> dict:
    req = urllib.request.Request(url=url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise SystemExit(f"[auth] ERROR: GET {url} -> HTTP {e.code}\nbody: {body_text}")


def _probe_session(server_url: str, api_version: str, access_token: str) -> dict | None:
    """Best-effort liveness check. Returns sessions/current JSON on 200, None otherwise."""
    req = urllib.request.Request(
        url=f"{server_url}/api/{api_version}/sessions/current",
        method="GET",
        headers={
            "Accept": "application/json",
            "X-Tableau-Auth": access_token,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None


def _new_server(server_url: str) -> "TSC.Server":
    """TSC.Server pinned to the highest REST API version the server supports.

    Calls use_server_version() explicitly: from tableauserverclient 0.41 the
    constructor flag no longer resolves the version up front, so `server.version`
    would stay at the 2.4 default and every REST call built from it would 404.
    The call fetches /api/<x>/serverinfo unauthenticated.
    """
    server = TSC.Server(server_url)
    server.use_server_version()
    return server


# ----- Session cache (outside the repository, so it is never committed or synced with the repo) -----
def _cache_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    root = Path(base) if base else Path.home() / ".config"
    return root / "samplehyperstore" / "session.json"


def _load_cached_session(server_url: str, site_name: str, api_version: str) -> dict | None:
    """Return {access_token, user_id} if cache matches (server, site) and token is still alive."""
    path = _cache_path()
    if not path.exists():
        return None
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[auth] cache unreadable, ignoring: {e}", file=sys.stderr)
        return None
    if cache.get("server_url") != server_url or cache.get("site_name") != site_name:
        return None
    access_token = cache.get("access_token")
    if not access_token:
        return None
    session = _probe_session(server_url, api_version, access_token)
    if session is None:
        print("[auth] cached token rejected by server, will re-auth", file=sys.stderr)
        try:
            path.unlink()
        except OSError:
            pass
        return None
    user_id = session["session"]["user"]["id"]
    print(f"[auth] reused cached session (user_id={user_id})", file=sys.stderr)
    return {"access_token": access_token, "user_id": user_id}


def _save_session(server_url: str, site_name: str, access_token: str) -> None:
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    payload = {
        "server_url": server_url,
        "site_name": site_name,
        "access_token": access_token,
    }
    # Create the file owner-only from the start (no window with default permissions on POSIX).
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, indent=2))
    os.replace(tmp, path)
    print(f"[auth] cached session at {path}", file=sys.stderr)


# ----- OAuth authorization_code (PKCE) flow -----
def _run_oauth_flow(server_url: str, site_name: str, port: int) -> str:
    """Drive PKCE browser sign-in. Returns access_token (3-part `id1|id2|site-luid`)."""
    redirect_uri = f"http://127.0.0.1:{port}/Callback"
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    client_id = str(uuid.uuid4())
    device_id = str(uuid.uuid4())

    result = _CallbackResult()
    handler_cls = _make_callback_handler(state, result)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler_cls)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[auth] callback listener: http://127.0.0.1:{port}/Callback", file=sys.stderr)

    auth_params = {
        "client_id": client_id,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "device_id": device_id,
        "device_name": "samplehyperstore-setup (python)",
        "target_site": site_name,
        "client_type": CLIENT_TYPE,
    }
    auth_url = f"{server_url}/oauth2/v1/auth?" + urllib.parse.urlencode(auth_params)
    print("[auth] opening browser for sign-in...", file=sys.stderr)
    webbrowser.open(auth_url)

    print(f"[auth] waiting for callback (up to {OAUTH_TIMEOUT_SECONDS}s)...", file=sys.stderr)
    received = result.event.wait(timeout=OAUTH_TIMEOUT_SECONDS)
    httpd.shutdown()
    httpd.server_close()
    if not received:
        raise SystemExit("[auth] ERROR: timeout waiting for OAuth callback")
    if result.error or not result.code:
        raise SystemExit(f"[auth] ERROR: callback error: {result.error!r}")

    token = _http_post_form(
        f"{server_url}/oauth2/v1/token",
        {
            "grant_type": "authorization_code",
            "code": result.code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        },
    )
    access_token = token["access_token"]
    print(f"[auth] access_token acquired (expires_in={token.get('expires_in')})", file=sys.stderr)
    return access_token


def _derive_site_luid(access_token: str) -> str:
    parts = access_token.split("|")
    if len(parts) != 3:
        raise SystemExit(
            f"[auth] ERROR: unexpected access_token shape (expected 3 parts, got {len(parts)})"
        )
    return parts[2]


def _fetch_user_id(server_url: str, api_version: str, access_token: str) -> str:
    session = _http_get_json(
        f"{server_url}/api/{api_version}/sessions/current",
        headers={
            "Accept": "application/json",
            "X-Tableau-Auth": access_token,
            "User-Agent": USER_AGENT,
        },
    )
    return session["session"]["user"]["id"]


@contextlib.contextmanager
def signed_in_server():
    """Yield a TSC.Server bound to a Tableau Cloud access_token.

    Reuses a cached token from the session cache (see _cache_path) when one is alive;
    otherwise runs OAuth (PKCE) browser sign-in and caches the result. Does NOT
    sign out on exit — call `python scripts/tableau_auth.py logout` to invalidate.
    """
    creds = load_credentials()
    server_url = creds["server_url"]
    site_name = creds["site_name"]
    port = creds["port"]

    server = _new_server(server_url)
    api_version = server.version

    cached = _load_cached_session(server_url, site_name, api_version)
    if cached:
        access_token = cached["access_token"]
        user_id = cached["user_id"]
        site_luid = _derive_site_luid(access_token)
    else:
        access_token = _run_oauth_flow(server_url, site_name, port)
        site_luid = _derive_site_luid(access_token)
        user_id = _fetch_user_id(server_url, api_version, access_token)
        _save_session(server_url, site_name, access_token)

    server._set_auth(site_luid, user_id, access_token, site_url=site_name)
    print(
        f"[auth] signed in: site_name={site_name!r} site_luid={site_luid} user_id={user_id}",
        file=sys.stderr,
    )

    yield server


# ----- CLI: logout / status -----
def _cli_logout() -> int:
    path = _cache_path()
    if not path.exists():
        print("[auth] no cached session to remove")
        return 0
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        cache = None
    if cache:
        server_url = cache.get("server_url")
        access_token = cache.get("access_token")
        if server_url and access_token:
            try:
                api_version = _new_server(server_url).version
                req = urllib.request.Request(
                    url=f"{server_url}/api/{api_version}/auth/signout",
                    method="POST",
                    headers={
                        "X-Tableau-Auth": access_token,
                        "User-Agent": USER_AGENT,
                    },
                )
                with urllib.request.urlopen(req, timeout=10):
                    pass
                print("[auth] server-side sign_out OK")
            except Exception as e:
                print(f"[auth] server-side sign_out best-effort failed: {e}")
    path.unlink()
    print(f"[auth] deleted cache: {path}")
    return 0


def _cli_status() -> int:
    path = _cache_path()
    print(f"cache path: {path}")
    if not path.exists():
        # 機械前チェック（バッチが実行可否を exit code で判定する）用に非 0 を返す。
        # このまま signed_in_server() を呼ぶとブラウザ待ちでハングするため。
        print("status: no cached session")
        return 1
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"status: unreadable ({e})")
        return 1
    server_url = cache.get("server_url")
    site_name = cache.get("site_name")
    access_token = cache.get("access_token")
    print(f"server_url: {server_url}")
    print(f"site_name: {site_name!r}")
    if not (server_url and access_token):
        print("status: malformed cache")
        return 1
    session = _probe_session(server_url, _new_server(server_url).version, access_token)
    if session is None:
        print("status: expired or invalid (next signed_in_server() will re-auth)")
        return 1
    user_id = session["session"]["user"]["id"]
    print(f"status: alive (user_id={user_id})")
    return 0


def _main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("logout", "status"):
        print("usage: python scripts/tableau_auth.py {logout|status}", file=sys.stderr)
        return 2
    if argv[1] == "logout":
        return _cli_logout()
    return _cli_status()


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
