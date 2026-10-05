import os
import secrets
import sqlite3
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
    PlainTextResponse,
)
from starlette.middleware.sessions import SessionMiddleware


# =========================================================
# POMP NET
# =========================================================

BRAND = "MR:Mohammad Pomp Net"
VERSION = "2026.10.05"
AUTHOR = "کدنویسی شده توسط تیم پمپ نت"

BASE_DIR = Path(__file__).resolve().parent

# Railway Volume:
# /data
# بدون Volume:
# فایل کنار پروژه ذخیره می‌شود
DATA_DIR = Path(
    os.getenv(
        "POMPNET_DATA_DIR",
        "/data"
    )
)

try:
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )
except Exception:
    DATA_DIR = BASE_DIR

DB_FILE = DATA_DIR / "pompnet2026.db"


# =========================================================
# LOGIN
# =========================================================

PANEL_USERNAME = os.getenv(
    "POMPNET_ADMIN_USERNAME",
    "PompNet-Mohammad"
)

PANEL_PASSWORD = os.getenv(
    "POMPNET_ADMIN_PASSWORD",
    "PompNet-Mohammad"
)

SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    "PompNet-Mohammad-2026-Secret"
)


# =========================================================
# EXTERNAL SERVICES
# =========================================================

CLOUDFLARE_API_TOKEN = os.getenv(
    "CLOUDFLARE_API_TOKEN",
    ""
)

CLOUDFLARE_ZONE_ID = os.getenv(
    "CLOUDFLARE_ZONE_ID",
    ""
)

GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    ""
)

GITHUB_REPOSITORY = os.getenv(
    "GITHUB_REPO",
    "uxurx7rh7e7xr73uue73e8/Mohammad-PompNet-Panel"
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title=BRAND,
    version=VERSION
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False
)


# =========================================================
# DATABASE
# =========================================================

def get_db():

    db = sqlite3.connect(
        str(DB_FILE),
        check_same_thread=False
    )

    db.row_factory = sqlite3.Row

    return db


def init_database():

    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protocol TEXT NOT NULL,
            link TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            username TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    db.commit()
    db.close()


init_database()


# =========================================================
# AUTH
# =========================================================

def is_logged_in(
    request: Request
):

    return (
        request.session.get(
            "pompnet_admin"
        ) is True
    )


def unauthorized():

    return JSONResponse(
        {
            "error": "unauthorized"
        },
        status_code=401
    )


# =========================================================
# LOGIN PAGE
# =========================================================

def login_page(
    error=""
):

    error_html = ""

    if error:

        error_html = f"""
        <div style="
            padding:12px;
            margin-bottom:15px;
            border-radius:12px;
            color:#ff9aaa;
            background:#35131f;
            border:1px solid #72263d;
            text-align:center;
        ">
            {error}
        </div>
        """

    return f"""
<!DOCTYPE html>

<html
    lang="fa"
    dir="rtl"
>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>
ورود | {BRAND}
</title>

<style>

* {{
    box-sizing:border-box;
}}

body {{

    margin:0;

    min-height:100vh;

    display:flex;

    justify-content:center;

    align-items:center;

    padding:20px;

    font-family:
        Tahoma,
        Arial,
        sans-serif;

    color:#fff;

    background:

        radial-gradient(
            circle at top right,
            #35106e,
            transparent 35%
        ),

        radial-gradient(
            circle at bottom left,
            #063d72,
            transparent 35%
        ),

        #04040a;
}}

.login {{

    width:min(
        440px,
        100%
    );

    padding:32px;

    border-radius:28px;

    background:
        rgba(12,10,25,.92);

    border:
        1px solid
        rgba(140,80,255,.45);

    box-shadow:
        0 25px 80px
        rgba(0,0,0,.55),

        0 0 60px
        rgba(100,40,255,.15);
}}

.logo {{

    text-align:center;

    font-size:25px;

    font-weight:900;
}}

.team {{

    text-align:center;

    color:#a9a0c4;

    margin-top:10px;

    line-height:2;
}}

input {{

    width:100%;

    padding:15px;

    margin-top:8px;

    margin-bottom:15px;

    border-radius:14px;

    border:
        1px solid
        #39275f;

    background:#080710;

    color:#fff;

    outline:none;
}}

button {{

    width:100%;

    border:0;

    padding:15px;

    border-radius:14px;

    color:#fff;

    font-weight:900;

    cursor:pointer;

    background:
        linear-gradient(
            90deg,
            #5526e8,
            #9c35df
        );
}}

.footer {{

    text-align:center;

    color:#777;

    font-size:11px;

    margin-top:20px;
}}

</style>

</head>

<body>

<div class="login">

<div class="logo">
🚀 {BRAND}
</div>

<div class="team">

{AUTHOR}

<br>

Version {VERSION}

</div>

{error_html}

<form
    method="post"
    action="/login"
>

<label>
نام کاربری
</label>

<input
    type="text"
    name="username"
    autocomplete="username"
    required
>

<label>
رمز عبور
</label>

<input
    type="password"
    name="password"
    autocomplete="current-password"
    required
>

<button type="submit">
🔐 ورود به پنل
</button>

</form>

<div class="footer">
PompNet • Mohammad • {VERSION}
</div>

</div>

</body>

</html>
"""


# =========================================================
# LOGIN ROUTES
# =========================================================

@app.get(
    "/login",
    response_class=HTMLResponse
)
async def login_get():

    return HTMLResponse(
        login_page()
    )


@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):

    username = username.strip()

    if (
        secrets.compare_digest(
            username,
            PANEL_USERNAME
        )
        and
        secrets.compare_digest(
            password,
            PANEL_PASSWORD
        )
    ):

        request.session.clear()

        request.session[
            "pompnet_admin"
        ] = True

        request.session[
            "username"
        ] = username

        return RedirectResponse(
            "/",
            status_code=303
        )

    return HTMLResponse(
        login_page(
            "❌ نام کاربری یا رمز عبور اشتباه است."
        ),
        status_code=401
    )


@app.get("/logout")
async def logout(
    request: Request
):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================================================
# MAIN PANEL
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def dashboard(
    request: Request
):

    if not is_logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    ui_file = (
        BASE_DIR /
        "pompnet_ui2026.html"
    )

    if not ui_file.exists():

        return HTMLResponse(
            "pompnet_ui2026.html پیدا نشد.",
            status_code=500
        )

    return HTMLResponse(
        ui_file.read_text(
            encoding="utf-8"
        )
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "ok": True,
        "status": "online",
        "panel": BRAND,
        "version": VERSION,
        "author": AUTHOR
    }


# =========================================================
# OVERVIEW
# =========================================================

@app.get("/api/overview")
async def overview(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    db = get_db()

    clients = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM clients
        """
    ).fetchone()["count"]

    bots = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM bots
        """
    ).fetchone()["count"]

    db.close()

    return {
        "brand": BRAND,
        "version": VERSION,
        "author": AUTHOR,
        "clients": clients,
        "bots": bots,
        "status": "online"
    }


# =========================================================
# PROTOCOL
# =========================================================

def detect_protocol(
    link: str
):

    value = (
        link
        .strip()
        .lower()
    )

    protocols = {

        "vless://": "VLESS",

        "vmess://": "VMESS",

        "trojan://": "Trojan",

        "ss://": "Shadowsocks",

        "hysteria2://":
            "Hysteria2",

        "hy2://":
            "Hysteria2",

        "tuic://":
            "TUIC"
    }

    for prefix, name in protocols.items():

        if value.startswith(prefix):

            return name

    return "Unknown"


# =========================================================
# CLIENTS
# =========================================================

@app.get("/api/clients")
async def list_clients(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    db = get_db()

    rows = db.execute(
        """
        SELECT
            id,
            name,
            protocol,
            link,
            token,
            created_at
        FROM clients
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return [
        dict(row)
        for row in rows
    ]


@app.post("/api/clients")
async def add_client(
    request: Request,
    name: str = Form(...),
    link: str = Form(...)
):

    if not is_logged_in(request):
        return unauthorized()

    name = name.strip()
    link = link.strip()

    if not name:

        return JSONResponse(
            {
                "ok": False,
                "error":
                    "نام کاربر خالی است"
            },
            status_code=400
        )

    if not link:

        return JSONResponse(
            {
                "ok": False,
                "error":
                    "لینک کانفیگ خالی است"
            },
            status_code=400
        )

    protocol = detect_protocol(
        link
    )

    if protocol == "Unknown":

        return JSONResponse(
            {
                "ok": False,
                "error":
                    "پروتکل کانفیگ پشتیبانی نمی‌شود"
            },
            status_code=400
        )

    token = secrets.token_urlsafe(
        24
    )

    db = get_db()

    db.execute(
        """
        INSERT INTO clients
        (
            name,
            protocol,
            link,
            token
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            protocol,
            link,
            token
        )
    )

    db.commit()
    db.close()

    return {
        "ok": True,
        "name": name,
        "protocol": protocol,
        "token": token,
        "subscription":
            f"/sub/{token}"
    }


@app.delete(
    "/api/clients/{client_id}"
)
async def delete_client(
    request: Request,
    client_id: int
):

    if not is_logged_in(request):
        return unauthorized()

    db = get_db()

    result = db.execute(
        """
        DELETE FROM clients
        WHERE id=?
        """,
        (client_id,)
    )

    db.commit()
    db.close()

    return {
        "ok":
            result.rowcount > 0
    }


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.get("/sub/{token}")
async def subscription(
    token: str
):

    db = get_db()

    rows = db.execute(
        """
        SELECT link
        FROM clients
        WHERE token=?
        """,
        (token,)
    ).fetchall()

    db.close()

    if not rows:

        return PlainTextResponse(
            "Subscription not found",
            status_code=404
        )

    links = []

    for row in rows:

        link = row["link"]

        if link:
            links.append(link)

    return PlainTextResponse(
        "\n".join(links),
        media_type="text/plain"
    )


# =========================================================
# TELEGRAM
# =========================================================

@app.get("/api/bots")
async def list_bots(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    db = get_db()

    rows = db.execute(
        """
        SELECT
            id,
            name,
            username,
            active,
            created_at
        FROM bots
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return [
        dict(row)
        for row in rows
    ]


@app.post("/api/bots/check")
async def check_bot(
    request: Request,
    token: str = Form(...)
):

    if not is_logged_in(request):
        return unauthorized()

    token = token.strip()

    if not token:

        return {
            "ok": False,
            "error":
                "Bot Token خالی است"
        }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                "https://api.telegram.org/"
                f"bot{token}/getMe"
            )

        data = response.json()

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc)
        }

    if not data.get("ok"):

        return {
            "ok": False,
            "error":
                "Bot Token معتبر نیست"
        }

    bot = data.get(
        "result",
        {}
    )

    username = bot.get(
        "username",
        ""
    )

    first_name = bot.get(
        "first_name",
        "Telegram Bot"
    )

    db = get_db()

    db.execute(
        """
        INSERT INTO bots
        (
            name,
            token,
            username,
            active
        )
        VALUES (?, ?, ?, 1)
        """,
        (
            first_name,
            token,
            username
        )
    )

    db.commit()
    db.close()

    return {
        "ok": True,
        "name": first_name,
        "username": username
    }


# =========================================================
# CLOUDFLARE
# =========================================================

@app.get("/api/cloudflare")
async def cloudflare(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    if not CLOUDFLARE_API_TOKEN:

        return {
            "configured": False,
            "connected": False,
            "message":
                "CLOUDFLARE_API_TOKEN تنظیم نشده"
        }

    headers = {
        "Authorization":
            f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type":
            "application/json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            if CLOUDFLARE_ZONE_ID:

                response = await client.get(
                    "https://api.cloudflare.com/"
                    "client/v4/zones/"
                    f"{CLOUDFLARE_ZONE_ID}",
                    headers=headers
                )

            else:

                response = await client.get(
                    "https://api.cloudflare.com/"
                    "client/v4/zones",
                    headers=headers
                )

        data = response.json()

        return {
            "configured": True,
            "connected":
                bool(
                    data.get("success")
                ),
            "data": data
        }

    except Exception as exc:

        return {
            "configured": True,
            "connected": False,
            "error": str(exc)
        }


# =========================================================
# GITHUB
# =========================================================

@app.get("/api/github")
async def github(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    if not GITHUB_TOKEN:

        return {
            "configured": False,
            "connected": False,
            "repository":
                GITHUB_REPOSITORY
        }

    headers = {
        "Authorization":
            f"Bearer {GITHUB_TOKEN}",
        "Accept":
            "application/vnd.github+json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                "https://api.github.com/repos/"
                + GITHUB_REPOSITORY,
                headers=headers
            )

        data = response.json()

        return {
            "configured": True,
            "connected":
                response.is_success,
            "repository":
                GITHUB_REPOSITORY,
            "private":
                data.get("private"),
            "default_branch":
                data.get(
                    "default_branch"
                ),
            "html_url":
                data.get("html_url")
        }

    except Exception as exc:

        return {
            "configured": True,
            "connected": False,
            "error": str(exc)
        }


# =========================================================
# RAILWAY
# =========================================================

@app.get("/api/railway")
async def railway(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    return {
        "platform": "Railway",
        "status": "running",
        "version": VERSION,
        "port":
            os.getenv(
                "PORT",
                ""
            ),
        "service":
            os.getenv(
                "RAILWAY_SERVICE_NAME",
                ""
            ),
        "environment":
            os.getenv(
                "RAILWAY_ENVIRONMENT_NAME",
                ""
            ),
        "deployment":
            os.getenv(
                "RAILWAY_DEPLOYMENT_ID",
                ""
            ),
        "domain":
            os.getenv(
                "RAILWAY_PUBLIC_DOMAIN",
                ""
            )
    }


# =========================================================
# CONFIG
# =========================================================

@app.get("/api/config")
async def config(
    request: Request
):

    if not is_logged_in(request):
        return unauthorized()

    return {
        "brand": BRAND,
        "author": AUTHOR,
        "version": VERSION,
        "runtime":
            "Python / FastAPI",
        "railway": True,
        "database":
            str(DB_FILE),
        "protocols": [
            "VLESS",
            "VMESS",
            "Trojan",
            "Shadowsocks",
            "Hysteria2",
            "TUIC"
        ]
    }


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "pompnet2026:app",
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "8080"
            )
        )
    )
