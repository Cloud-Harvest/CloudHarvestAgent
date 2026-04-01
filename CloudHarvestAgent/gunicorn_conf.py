# python
import os
import socket

# Bind address
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8500")

# TLS: prefer explicit GUNICORN_CERTFILE / GUNICORN_KEYFILE, fall back to PEMFILE for both
_pem = os.getenv("PEMFILE", './app/harvest-self-signed.pem')
certfile = os.getenv("GUNICORN_CERTFILE") or _pem or None
keyfile = os.getenv("GUNICORN_KEYFILE") or _pem or None

# Worker count: prefer HARVEST_AGENT_WORKERS, fall back to launcher default (5)
workers = int(os.getenv("HARVEST_AGENT_WORKERS", "5"))

# Worker class and threads tuned for I/O-bound workloads (requests.Session() pooling)
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", "25"))

# Keep connections alive longer so requests.Session() pools remain usable
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "75"))

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Avoid frequent worker recycling which drops pooled connections
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "0"))

# Networking tuning
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))
reuse_port = True

# Do not preload the app (preload can create shared connection pools that become invalid after fork)
preload_app = False

# Request limits (keep reasonable defaults)
limit_request_line = int(os.getenv("GUNICORN_LIMIT_REQUEST_LINE", "4094"))
limit_request_fields = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELDS", "100"))
limit_request_field_size = int(os.getenv("GUNICORN_LIMIT_REQUEST_FIELD_SIZE", "8190"))

# Logging
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")

def when_ready(server):
    """
    Try to enable TCP keepalive on listener sockets so the kernel probes dead peers.
    Fallbacks are guarded to avoid failing gunicorn startup on unsupported platforms.
    """
    try:
        for sock in getattr(server, "sockets", []) or []:
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # Linux-specific tuning (guarded)
                if hasattr(socket, "TCP_KEEPIDLE"):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                if hasattr(socket, "TCP_KEEPINTVL"):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
                if hasattr(socket, "TCP_KEEPCNT"):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 6)
            except Exception:
                server.log.debug("Failed to set keepalive on socket", exc_info=True)
    except Exception:
        # Keep startup resilient; log the fact but do not abort
        try:
            server.log.info("Could not set TCP keepalive on sockets", exc_info=True)
        except Exception:
            pass

def post_fork(server, worker):
    # Helpful for debugging worker lifecycle while tuning
    server.log.info("Worker spawned (pid: %s)", getattr(worker, "pid", "unknown"))
