from __future__ import annotations

import asyncio
import ipaddress
import ssl
import socket
from urllib.parse import urljoin, urlparse

CURATED_RESOURCES = [
    {"title": "Python Tutorial", "resource_type": "website", "url": "https://docs.python.org/3/tutorial/"},
    {"title": "FastAPI Tutorial", "resource_type": "website", "url": "https://fastapi.tiangolo.com/tutorial/"},
    {"title": "MDN Web Docs", "resource_type": "website", "url": "https://developer.mozilla.org/"},
    {"title": "freeCodeCamp", "resource_type": "website", "url": "https://www.freecodecamp.org/learn/"},
    {"title": "Khan Academy", "resource_type": "website", "url": "https://www.khanacademy.org/"},
    {"title": "Git Documentation", "resource_type": "website", "url": "https://git-scm.com/doc"},
]
CURATED_URLS = {r["url"] for r in CURATED_RESOURCES}


async def _public_host(host: str) -> bool:
    if host.casefold().rstrip(".") in {"localhost", "localhost.localdomain"}:
        return False
    try:
        literal = ipaddress.ip_address(host.split("%", 1)[0])
        return literal.is_global
    except ValueError:
        pass
    try:
        results = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM), timeout=1.0)
    except (OSError, asyncio.TimeoutError):
        return False
    if not results:
        return False
    for item in results:
        try:
            address = ipaddress.ip_address(item[4][0].split("%", 1)[0])
        except ValueError:
            return False
        if not address.is_global:
            return False
    return True


async def _head_pinned(url: str) -> tuple[int, str | None]:
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    infos = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(
        parsed.hostname, port, type=socket.SOCK_STREAM), timeout=1.0)
    addresses = []
    for item in infos:
        ip = ipaddress.ip_address(item[4][0].split("%", 1)[0])
        if not ip.is_global:
            raise ValueError("non-public host")
        addresses.append(str(ip))
    if not addresses:
        raise ValueError("host did not resolve")
    reader = writer = None
    try:
        ssl_context = ssl.create_default_context() if parsed.scheme == "https" else None
        reader, writer = await asyncio.wait_for(asyncio.open_connection(
            addresses[0], port, ssl=ssl_context,
            server_hostname=parsed.hostname if ssl_context else None), timeout=2.0)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        host_header = parsed.hostname if parsed.port is None else f"{parsed.hostname}:{port}"
        writer.write(f"HEAD {path} HTTP/1.1\r\nHost: {host_header}\r\nUser-Agent: FinishAI-Resource-Check/1.0\r\nConnection: close\r\n\r\n".encode("ascii"))
        await asyncio.wait_for(writer.drain(), timeout=1.0)
        status_line = await asyncio.wait_for(reader.readline(), timeout=1.0)
        parts = status_line.decode("latin-1").split()
        if len(parts) < 2 or not parts[1].isdigit():
            raise ValueError("invalid response")
        status = int(parts[1])
        location = None
        header_bytes = 0
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=1.0)
            header_bytes += len(line)
            if header_bytes > 8192 or not line:
                raise ValueError("response headers too large or incomplete")
            if line in (b"\r\n", b"\n"):
                break
            name, sep, value = line.decode("latin-1").partition(":")
            if sep and name.lower() == "location":
                location = value.strip()
        return status, location
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass


async def verify_url(url: str) -> bool:
    """Validate each redirect destination and make a bounded anonymous HEAD request."""
    current = url
    for _ in range(4):
        parsed = urlparse(current)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        if current in CURATED_URLS:
            return True
        if not await _public_host(parsed.hostname):
            return False
        try:
            status, location = await asyncio.wait_for(_head_pinned(current), timeout=3.0)
        except (OSError, ValueError, asyncio.TimeoutError):
            return False
        if 200 <= status < 300:
            return True
        if status in {301, 302, 303, 307, 308}:
            if not location:
                return False
            current = urljoin(current, location)
            continue
        return False
    return False
