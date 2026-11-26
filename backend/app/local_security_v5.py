
# CONCILIA_V5_LOCAL_SECURITY_30A5A

import os
from pathlib import Path
from urllib.parse import urlsplit

from starlette.responses import JSONResponse


LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1"
}

# Suporte automatico para Azure App Service e dominios customizados
AZURE_HOSTNAME = os.getenv("WEBSITE_HOSTNAME", "").strip()
if AZURE_HOSTNAME:
    LOCAL_HOSTS.add(AZURE_HOSTNAME.lower())
    LOCAL_HOSTS.add(AZURE_HOSTNAME.split(":")[0].lower())

EXTRA_ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").strip()
if EXTRA_ALLOWED_HOSTS:
    for h in EXTRA_ALLOWED_HOSTS.split(","):
        h_clean = h.strip().lower()
        if h_clean:
            LOCAL_HOSTS.add(h_clean)
            LOCAL_HOSTS.add(h_clean.split(":")[0])

LOCAL_PORTS = {
    80,
    443,
    3000,
    8000,
    8001,
    8013
}

ALLOWED_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1", "[::1]")
    for port in sorted(LOCAL_PORTS)
]

if AZURE_HOSTNAME:
    ALLOWED_ORIGINS.extend([
        f"https://{AZURE_HOSTNAME}",
        f"http://{AZURE_HOSTNAME}"
    ])

if EXTRA_ALLOWED_HOSTS:
    for h in EXTRA_ALLOWED_HOSTS.split(","):
        h_clean = h.strip().lower()
        if h_clean:
            ALLOWED_ORIGINS.extend([
                f"https://{h_clean}",
                f"http://{h_clean}"
            ])


def valid_local_host(value):
    if os.getenv("ALLOW_ALL_HOSTS", "false").lower() in ("true", "1", "yes"):
        return True

    try:
        parsed = urlsplit("http://" + value)
        host = (parsed.hostname or "").lower()

        return (
            host in LOCAL_HOSTS
            or host.endswith(".azurewebsites.net")
            and parsed.username is None
            and parsed.password is None
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
            and (
                parsed.port is None
                or 1 <= parsed.port <= 65535
            )
        )

    except (ValueError, TypeError):
        return False


def valid_local_origin(value, host=None):

    if not isinstance(value, str):
        return False

    if value in ALLOWED_ORIGINS:
        return True

    if host and valid_local_host(host):
        return value in ("http://" + host, "https://" + host)

    return False


def safe_static_path(root, requested):

    if not isinstance(requested, str):
        raise ValueError("Caminho invalido.")

    if (
        "\\" in requested
        or "\x00" in requested
        or ":" in requested
        or requested.startswith("/")
        or any(
            part == ".."
            for part in requested.split("/")
        )
    ):
        raise ValueError("Caminho nao autorizado.")

    base = Path(root).resolve()
    candidate = (base / requested).resolve()

    if not candidate.is_relative_to(base):
        raise ValueError("Caminho fora do frontend.")

    return candidate


class LocalSecurityMiddlewareV5:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_headers = scope.get("headers", [])

        hosts = [
            v.decode("latin-1")
            for k, v in raw_headers
            if k.lower() == b"host"
        ]

        origins = [
            v.decode("latin-1")
            for k, v in raw_headers
            if k.lower() == b"origin"
        ]

        fetch_sites = [
            v.decode("latin-1")
            for k, v in raw_headers
            if k.lower() == b"sec-fetch-site"
        ]

        path = scope.get("path", "")
        is_api = path == "/api" or path.startswith("/api/")

        async def secure_send(message):

            if message["type"] == "http.response.start":

                headers = list(message.get("headers", []))

                security_headers = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"cross-origin-resource-policy": b"same-site"
                }

                if is_api:
                    security_headers[b"cache-control"] = b"no-store"

                headers = [
                    (key, value)
                    for key, value in headers
                    if key.lower() not in security_headers
                ]

                headers.extend(security_headers.items())
                message["headers"] = headers

            await send(message)

        async def reject(status, detail):

            response = JSONResponse(
                {"detail": detail},
                status_code=status
            )

            await response(scope, receive, secure_send)

        if len(hosts) != 1 or not valid_local_host(hosts[0]):

            await reject(400, "Host nao autorizado.")
            return

        if len(origins) > 1:

            await reject(403, "Origem invalida.")
            return

        if origins and not valid_local_origin(
            origins[0],
            hosts[0]
        ):

            await reject(403, "Origem nao autorizada.")
            return

        if is_api and "cross-site" in fetch_sites:

            await reject(403, "Requisicao externa bloqueada.")
            return

        await self.app(scope, receive, secure_send)
