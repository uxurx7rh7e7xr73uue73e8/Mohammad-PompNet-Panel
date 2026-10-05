import os
import time


START_TIME = time.time()


def health():
    return {
        "ok": True,
        "status": "online",
        "runtime": "Python / FastAPI",
        "version": "2026.10.05",
        "uptime_seconds": int(
            time.time() - START_TIME
        ),
        "port": os.getenv(
            "PORT",
            ""
        )
    }
