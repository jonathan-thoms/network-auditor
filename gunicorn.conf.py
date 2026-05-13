# Gunicorn configuration file
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing

# Bind to localhost; Nginx will reverse-proxy to this
bind = "127.0.0.1:8000"

# Workers = 2 × CPU cores + 1  (safe default for a small droplet)
workers = multiprocessing.cpu_count() * 2 + 1

# Timeout (seconds) — increase if audit processing is slow
timeout = 300

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Restart workers after this many requests (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50
