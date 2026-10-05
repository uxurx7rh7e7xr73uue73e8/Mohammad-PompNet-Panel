import os
import time


START_TIME = time.time()


def health():

    uptime = int(
        time.time()
        - START_TIME
    )

    return {

        "ok": True,

        "status":
            "online",

        "runtime":
            "Python / FastAPI",

        "uptime_seconds":
            uptime,

        "port":
            os.getenv(
                "PORT",
                ""
            )

    }
