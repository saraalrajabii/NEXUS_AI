"""Production entry point: `python -m app.serve`.

Why not just `uvicorn --host ::`? With an IPv6 host, Python's asyncio makes the socket
IPv6-ONLY. Hosting platforms differ: Railway's private network uses IPv6 while its health
checks arrive over IPv4. So we open ONE "dual-stack" socket that accepts both, and fall back
to plain IPv4 where the machine has no IPv6.

Environment: PORT (default 8000), HOST (default "::" = all addresses, IPv4 + IPv6).
"""

import logging
import os
import socket

import uvicorn

log = logging.getLogger("nexus.serve")


def make_socket(host: str, port: int) -> socket.socket:
    if ":" in host:
        try:
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # also accept IPv4
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return sock
        except OSError as exc:
            log.warning("IPv6 not available (%s); listening on IPv4 only", exc)
            host = "0.0.0.0"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    return sock


def main() -> None:
    host = os.environ.get("HOST", "::")
    port = int(os.environ.get("PORT", "8000"))
    sock = make_socket(host, port)
    family = "IPv4+IPv6" if sock.family == socket.AF_INET6 else "IPv4"
    print(f"[serve] Listening on port {port} ({family})", flush=True)
    config = uvicorn.Config("app.main:app", proxy_headers=True, forwarded_allow_ips="*")
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
