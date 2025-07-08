# Gunicorn configuration file for Google Calendar Sync
import os

# Server socket
bind = "0.0.0.0:5000"  # Use port 5000 for consistency
backlog = 2048

# Worker processes
workers = 2  # Recommended: (2 x num_cores) + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increased for AI processing
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Process naming
proc_name = "calendar-sync"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Environment
raw_env = [
    "PYTHONUNBUFFERED=1",
]

# SSL (uncomment for HTTPS)
# keyfile = "path/to/keyfile"
# certfile = "path/to/certfile" 