#!/usr/bin/env python3
"""
SAS PRODUCTION SERVER — waitress (Windows-friendly, no Flask debug).

Serves the same Flask app as jacky_api.py but through a real WSGI server so it
can safely sit behind the Cloudflare Tunnel and face the internet.

Run:  python serve.py
Env:  SAS_HOST (default 0.0.0.0), SAS_PORT (default 5000), SAS_THREADS (8)
"""

import os
import logging
from waitress import serve

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("SAS-Serve")

from jacky_api import app, REQUIRE_AUTH  # imports + builds the engine once

if __name__ == "__main__":
    host = os.getenv("SAS_HOST", "0.0.0.0")
    port = int(os.getenv("SAS_PORT", "5000"))
    threads = int(os.getenv("SAS_THREADS", "8"))

    log.info("=" * 60)
    log.info("SAS production server (waitress)")
    log.info(f"  Local:  http://localhost:{port}/dashboard")
    log.info(f"  Bind:   {host}:{port}  threads={threads}")
    log.info(f"  Auth:   {'ENABLED (login required)' if REQUIRE_AUTH else 'DISABLED — LAN only, do NOT expose!'}")
    log.info("=" * 60)

    serve(app, host=host, port=port, threads=threads, ident="SAS")
