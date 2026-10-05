import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    PlainTextResponse,
)
from starlette.middleware.sessions import SessionMiddleware


# =========================================================
# POMP NET
# MR:Mohammad Pomp Net
# Python + FastAPI
# Railway Ready
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

APP_NAME = "MR:Mohammad Pomp Net"
VERSION = "2026.10.05"

DB_FILE = BASE_DIR / "pompnet.db"
UI_FILE = BASE_DIR / "pompnet_ui2026.html"

ADMIN_PASSWORD = os.getenv(
    "POMPNET_ADMIN_PASSWORD",
    "Mohammad@2026"
)

SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    "PompNet-Change-This-Secret"
)


app = FastAPI(
    title=APP_NAME,
    version=VERSION
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protocol TEXT NOT NULL,
            link TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            username TEXT DEFAULT '',
            status TEXT DEFAULT 'unknown',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


init_database()


# =========================================================
# AUTH
# =========================================================

def is_logged_in(request: Request):

    return request.session.get("admin") is True


def require_auth(request: Request):

    if not is_logged_in(request):

        return JSONResponse(
            {
                "ok": False,
                "error": "unauthorized"
            },
            status_code=401
        )

    return None


# =========================================================
# PROTOCOL DETECTION
# =========================================================

def detect_protocol(link: str):

    value = link.strip().lower()

    protocols = {
        "vless://": "VLESS",
        "vmess://": "VMESS",
        "trojan://": "Trojan",
        "ss://": "Shadowsocks",
        "hysteria2://": "Hysteria2",
        "hy2://": "Hysteria2",
        "tuic://": "TUIC",
    }

    for prefix, protocol in protocols.items():

        if value.startswith(prefix):
            return protocol

    return "Unknown"


# =========================================================
# LOGIN PAGE
# =========================================================

@app.get(
    "/login",
    response_class=HTMLResponse
)
async def login_page(request: Request):

    if is_logged_in(request):

        return RedirectResponse(
            "/",
            status_code=303
        )

    return HTMLResponse("""
<!DOCTYPE html>

<html lang="fa" dir="rtl">

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width,initial-scale=1"
>

<title>ورود | Mohammad Pomp Net</title>

<style>

*{
box-sizing:border-box;
}

body{

margin:0;

min-height:100vh;

display:flex;

align-items:center;

justify-content:center;

font-family:Tahoma,Arial,sans-serif;

background:

radial-gradient(
circle at top,
#321078,
transparent 40%
),

#05030b;

color:white;

}

.box{

width:min(430px,92%);

padding:30px;

border-radius:26px;

background:
rgba(13,8,28,.9);

border:
1px solid
rgba(135,75,255,.5);

box-shadow:
0 25px 80px
rgba(0,0,0,.5);

}

.logo{

text-align:center;

font-size:25px;

font-weight:900;

margin-bottom:10px;

}

.subtitle{

text-align:center;

color:#aaa;

margin-bottom:25px;

}

input{

width:100%;

padding:15px;

border-radius:14px;

border:1px solid #392269;

background:#080610;

color:white;

outline:none;

margin-bottom:15px;

}

button{

width:100%;

padding:15px;

border:0;

border-radius:14px;

background:
linear-gradient(
90deg,
#6335ff,
#a938ed
);

color:white;

font-weight:900;

cursor:pointer;

}

</style>

</head>

<body>

<div class="box">

<div class="logo">
🚀 MR:Mohammad Pomp Net
</div>

<div class="subtitle">
پنل مدیریت
</div>

<form
method="post"
action="/login"
>

<input
type="password"
name="password"
placeholder="رمز مدیریت"
required
>

<button>
ورود
</button>

</form>

</div>

</body>

</html>
""")


@app.post("/login")
async def login(
    request: Request,
    password: str = Form(...)
):

    if secrets.compare_digest(
        password,
        ADMIN_PASSWORD
    ):

        request.session["admin"] = True

        return RedirectResponse(
            "/",
            status_code=303
        )

    return HTMLResponse(
        """
        <div
        dir="rtl"
        style="
        background:#05030b;
        color:white;
        min-height:100vh;
        padding:80px;
        text-align:center;
        font-family:Tahoma;
        ">
        <h2>❌ رمز اشتباه است</h2>
        <a
        href="/login"
        style="color:#a978ff">
        بازگشت
        </a>
        </div>
        """,
        status_code=401
    )


@app.get("/logout")
async def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================================================
# MAIN UI
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def home(request: Request):

    if not is_logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    if not UI_FILE.exists():

        return HTMLResponse(
            """
            <h2>فایل UI پیدا نشد</h2>
            <p>
            فایل
            pompnet_ui2026.html
            را کنار
            pompnet2026.py
            قرار دهید.
            </p>
            """,
            status_code=500
        )

    return HTMLResponse(
        UI_FILE.read_text(
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
        "name": APP_NAME,
        "version": VERSION,
        "runtime": "Python FastAPI",
        "database": "SQLite"
    }


# =========================================================
# OVERVIEW
# =========================================================

@app.get("/api/overview")
async def overview(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    connection = get_db()

    clients = connection.execute(
        "SELECT COUNT(*) AS total FROM clients"
    ).fetchone()["total"]

    bots = connection.execute(
        "SELECT COUNT(*) AS total FROM bots"
    ).fetchone()["total"]

    connection.close()

    return {

        "ok": True,

        "name": APP_NAME,

        "version": VERSION,

        "clients": clients,

        "bots": bots,

        "status": "online"

    }


# =========================================================
# VPN CLIENTS
# =========================================================

@app.get("/api/clients")
async def clients(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    connection = get_db()

    rows = connection.execute("""
        SELECT
            id,
            name,
            protocol,
            link,
            token,
            created_at
        FROM clients
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return {
        "ok": True,
        "clients": [
            dict(row)
            for row in rows
        ]
    }


@app.post("/api/clients")
async def create_client(
    request: Request,
    name: str = Form(...),
    link: str = Form(...)
):

    auth = require_auth(request)

    if auth:
        return auth

    name = name.strip()
    link = link.strip()

    if not name:

        return JSONResponse(
            {
                "ok": False,
                "error":
                "نام کاربر وارد نشده است."
            },
            status_code=400
        )

    protocol = detect_protocol(link)

    if protocol == "Unknown":

        return JSONResponse(
            {
                "ok": False,
                "error":
                "فرمت لینک پشتیبانی نمی‌شود."
            },
            status_code=400
        )

    token = secrets.token_urlsafe(24)

    connection = get_db()

    connection.execute("""
        INSERT INTO clients
        (
            name,
            protocol,
            link,
            token
        )
        VALUES
        (?, ?, ?, ?)
    """, (
        name,
        protocol,
        link,
        token
    ))

    connection.commit()

    connection.close()

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
async def remove_client(
    request: Request,
    client_id: int
):

    auth = require_auth(request)

    if auth:
        return auth

    connection = get_db()

    connection.execute(
        "DELETE FROM clients WHERE id=?",
        (client_id,)
    )

    connection.commit()

    connection.close()

    return {
        "ok": True,
        "deleted": client_id
    }


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.get(
    "/sub/{token}",
    response_class=PlainTextResponse
)
async def subscription(
    token: str
):

    connection = get_db()

    rows = connection.execute("""
        SELECT link
        FROM clients
        WHERE token=?
    """, (token,)).fetchall()

    connection.close()

    if not rows:

        return PlainTextResponse(
            "Subscription not found",
            status_code=404
        )

    links = []

    for row in rows:

        links.append(
            row["link"]
        )

    return PlainTextResponse(
        "\n".join(links)
    )


# =========================================================
# TELEGRAM BOTS
# =========================================================

@app.get("/api/bots")
async def get_bots(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    connection = get_db()

    rows = connection.execute("""
        SELECT
            id,
            name,
            username,
            status,
            created_at
        FROM bots
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return {
        "ok": True,
        "bots": [
            dict(row)
            for row in rows
        ]
    }


@app.post("/api/bots/check")
async def check_bot(
    request: Request,
    token: str = Form(...)
):

    auth = require_auth(request)

    if auth:
        return auth

    token = token.strip()

    if not token:

        return JSONResponse(
            {
                "ok": False,
                "error":
                "Bot Token خالی است."
            },
            status_code=400
        )

    import urllib.request
    import json

    url = (
        "https://api.telegram.org/"
        f"bot{token}/getMe"
    )

    try:

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                "Mohammad-PompNet"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=15
        ) as response:

            data = json.loads(
                response.read().decode()
            )

        if not data.get("ok"):

            return JSONResponse(
                {
                    "ok": False,
                    "error":
                    "Bot Token معتبر نیست."
                },
                status_code=400
            )

        bot = data["result"]

        connection = get_db()

        connection.execute("""
            INSERT INTO bots
            (
                name,
                token,
                username,
                status
            )
            VALUES
            (?, ?, ?, ?)
        """, (
            bot.get(
                "first_name",
                "Telegram Bot"
            ),
            token,
            bot.get(
                "username",
                ""
            ),
            "online"
        ))

        connection.commit()

        connection.close()

        return {

            "ok": True,

            "id":
            bot.get("id"),

            "name":
            bot.get("first_name"),

            "username":
            bot.get("username")

        }

    except Exception as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": str(exc)
            },
            status_code=500
        )


# =========================================================
# CLOUDFLARE
# =========================================================

@app.get("/api/cloudflare")
async def cloudflare(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    token = os.getenv(
        "CLOUDFLARE_API_TOKEN",
        ""
    ).strip()

    zone_id = os.getenv(
        "CLOUDFLARE_ZONE_ID",
        ""
    ).strip()

    if not token:

        return {
            "ok": True,
            "configured": False,
            "message":
            "CLOUDFLARE_API_TOKEN تنظیم نشده است."
        }

    try:

        import urllib.request

        headers = {
            "Authorization":
            f"Bearer {token}"
        }

        url = (
            "https://api.cloudflare.com/"
            "client/v4/zones"
        )

        req = urllib.request.Request(
            url,
            headers=headers
        )

        with urllib.request.urlopen(
            req,
            timeout=15
        ) as response:

            data = json_loads_safe(
                response.read()
            )

        return {
            "ok": True,
            "configured": True,
            "success":
            data.get("success", False),
            "result":
            data.get("result", [])
        }

    except Exception as exc:

        return {
            "ok": False,
            "configured": True,
            "error": str(exc)
        }


# =========================================================
# GITHUB
# =========================================================

@app.get("/api/github")
async def github(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    token = os.getenv(
        "GITHUB_TOKEN",
        ""
    ).strip()

    repo = os.getenv(
        "GITHUB_REPO",
        "uxurx7rh7e7xr73uue73e8/"
        "Mohammad-PompNet-Panel"
    ).strip()

    if not token:

        return {
            "ok": True,
            "configured": False,
            "repository": repo
        }

    try:

        import urllib.request

        url = (
            "https://api.github.com/repos/"
            + repo
        )

        req = urllib.request.Request(
            url,
            headers={
                "Authorization":
                f"Bearer {token}",
                "Accept":
                "application/vnd.github+json"
            }
        )

        with urllib.request.urlopen(
            req,
            timeout=15
        ) as response:

            data = json_loads_safe(
                response.read()
            )

        return {
            "ok": True,
            "configured": True,
            "repository": repo,
            "name":
            data.get("name"),
            "private":
            data.get("private"),
            "branch":
            data.get("default_branch")
        }

    except Exception as exc:

        return {
            "ok": False,
            "configured": True,
            "error": str(exc)
        }


# =========================================================
# RAILWAY
# =========================================================

@app.get("/api/railway")
async def railway(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    return {

        "ok": True,

        "platform":
        "Railway",

        "runtime":
        "Python FastAPI",

        "port":
        os.getenv(
            "PORT",
            "8080"
        ),

        "status":
        "ready"

    }


# =========================================================
# CONFIG
# =========================================================

@app.get("/api/config")
async def config(
    request: Request
):

    auth = require_auth(request)

    if auth:
        return auth

    return {

        "ok": True,

        "name":
        APP_NAME,

        "version":
        VERSION,

        "runtime":
        "Python",

        "framework":
        "FastAPI",

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
# SAFE JSON
# =========================================================

def json_loads_safe(data):

    import json

    return json.loads(
        data.decode(
            "utf-8"
        )
    )


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
