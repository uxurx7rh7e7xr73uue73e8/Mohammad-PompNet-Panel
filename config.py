import os


APP_NAME = os.getenv(
    "POMPNET_APP_NAME",
    "MR:Mohammad Pomp Net"
)

APP_VERSION = "2026.10.05"

TIMEZONE = os.getenv(
    "POMPNET_TIMEZONE",
    "Asia/Tehran"
)

DATABASE_PATH = os.getenv(
    "POMPNET_DATABASE",
    "/data/pompnet.db"
)

ADMIN_USER = os.getenv(
    "POMPNET_ADMIN_USER",
    "admin"
)

ADMIN_PASSWORD = os.getenv(
    "POMPNET_ADMIN_PASSWORD",
    ""
)

SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    ""
)

GITHUB_REPOSITORY = os.getenv(
    "GITHUB_REPO",
    "uxurx7rh7e7xr73uue73e8/Mohammad-PompNet-Panel"
)

GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    ""
)

CLOUDFLARE_API_TOKEN = os.getenv(
    "CLOUDFLARE_API_TOKEN",
    ""
)

CLOUDFLARE_ZONE_ID = os.getenv(
    "CLOUDFLARE_ZONE_ID",
    ""
)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
)

SANEAI_URL = os.getenv(
    "SANEAI_URL",
    os.getenv("XUI_URL", "")
).rstrip("/")

SANEAI_USERNAME = os.getenv(
    "SANEAI_USERNAME",
    os.getenv("XUI_USERNAME", "")
)

SANEAI_PASSWORD = os.getenv(
    "SANEAI_PASSWORD",
    os.getenv("XUI_PASSWORD", "")
)

SANEAI_TOKEN = os.getenv(
    "SANEAI_TOKEN",
    os.getenv("XUI_TOKEN", "")
)

SUBSCRIPTION_BASE_URL = os.getenv(
    "SUBSCRIPTION_BASE_URL",
    ""
)

PORT = int(
    os.getenv("PORT", "8080")
)
