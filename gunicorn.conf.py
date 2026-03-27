import os

# Worker class — gevent enables async I/O for SSE streaming
worker_class = "gevent"

# 2 workers for POC/demo (1 per CPU core is standard for gevent)
workers = int(os.getenv("GUNICORN_WORKERS", "2"))

# Greenlets per worker — each SSE connection = 1 greenlet
worker_connections = int(os.getenv("GUNICORN_CONNECTIONS", "50"))

# Bind address
bind = f"{os.getenv('FLASK_HOST', '0.0.0.0')}:{os.getenv('FLASK_PORT', '5000')}"

# Timeouts — AI responses can take 60–90s; set higher than OPENROUTER_TIMEOUT
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = 5

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Graceful restart window
graceful_timeout = 30
