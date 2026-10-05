import os
import secrets
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

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

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "pompnet2026.db"

BRAND = "MR:Mohammad Pomp Net"
VERSION = "2026.10.05"
AUTHOR = "کدنویسی شده توسط تیم پمپ نت"

PANEL_USERNAME = os.getenv(
    "POMPNET_ADMIN_USERNAME",
    "PompNet-Mohammad",
)

PANEL_PASSWORD = os.getenv(
    "POMPNET_ADMIN_PASSWORD",
    "PompNet-Mohammad",
)

SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    "PompNet-Mohammad-2026-Secret",
)


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title=BRAND,
    version=VERSION,
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
    db = sqlite3.connect(DB_FILE)
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

def is_logged_in(request: Request):
    return request.session.get("pompnet_admin") is True


def login_page(error=""):

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
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ورود | {BRAND}</title>

<style>
*{{box-sizing:border-box}}

body{{
    margin:0;
    min-height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:20px;
    font-family:Tahoma,Arial,sans-serif;
    color:#fff;
    background:
        radial-gradient(circle at top right,#35106e,transparent 35%),
        radial-gradient(circle at bottom left,#063d72,transparent 35%),
        #04040a;
}}

.login{{
    width:min(440px,100%);
    padding:32px;
    border-radius:28px;
    background:rgba(12,10,25,.9);
    border:1px solid rgba(140,80,255,.45);
    box-shadow:
        0 25px 80px rgba(0,0,0,.55),
        0 0 60px rgba(100,40,255,.15);
}}

.logo{{
    text-align:center;
    font-size:25px;
    font-weight:900;
}}

.team{{
    text-align:center;
    color:#a9a0c4;
    margin-top:10px;
    line-height:2;
}}

input{{
    width:100%;
    padding:15px;
    margin-top:8px;
    margin-bottom:15px;
    border-radius:14px;
    border:1px solid #39275f;
    background:#080710;
    color:#fff;
    outline:none;
}}

button{{
    width:100%;
    border:0;
    padding:15px;
    border-radius:14px;
    color:#fff;
    font-weight:900;
    cursor:pointer;
    background:linear-gradient(90deg,#5526e8,#9c35df);
}}

.footer{{
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
{AUTHOR}<br>
Version {VERSION}
</div>

{error_html}

<form method="post" action="/login">

<label>نام کاربری</label>
<input
    type="text"
    name="username"
    autocomplete="username"
    required
>

<label>رمز عبور</label>
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


@app.get("/login", response_class=HTMLResponse)
async def login_get():
    return HTMLResponse(login_page())


@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):

    username = username.strip()

    if (
        secrets.compare_digest(username, PANEL_USERNAME)
        and secrets.compare_digest(password, PANEL_PASSWORD)
    ):
        request.session.clear()
        request.session["pompnet_admin"] = True
        request.session["username"] = username

        return RedirectResponse(
            "/",
            status_code=303,
        )

    return HTMLResponse(
        login_page(
            "❌ نام کاربری یا رمز عبور اشتباه است."
        ),
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303,
    )


# =========================================================
# MAIN PANEL
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    if not is_logged_in(request):
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    ui = BASE_DIR / "pompnet_ui2026.html"

    if not ui.exists():
        return HTMLResponse(
            "pompnet_ui2026.html پیدا نشد.",
            status_code=500,
        )

    return HTMLResponse(
        ui.read_text(encoding="utf-8")
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "panel": BRAND,
        "version": VERSION,
        "author": AUTHOR,
    }


# =========================================================
# OVERVIEW
# =========================================================

@app.get("/api/overview")
async def overview(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    db = get_db()

    clients = db.execute(
        "SELECT COUNT(*) AS c FROM clients"
    ).fetchone()["c"]

    bots = db.execute(
        "SELECT COUNT(*) AS c FROM bots"
    ).fetchone()["c"]

    db.close()

    return {
        "brand": BRAND,
        "version": VERSION,
        "author": AUTHOR,
        "clients": clients,
        "bots": bots,
        "status": "online",
    }


# =========================================================
# CLIENTS
# =========================================================

def detect_protocol(link: str):

    value = link.strip().lower()

    if value.startswith("vless://"):
        return "VLESS"

    if value.startswith("vmess://"):
        return "VMESS"

    if value.startswith("trojan://"):
        return "Trojan"

    if value.startswith("ss://"):
        return "Shadowsocks"

    if value.startswith("hysteria2://"):
        return "Hysteria2"

    if value.startswith("tuic://"):
        return "TUIC"

    return "Unknown"


@app.get("/api/clients")
async def list_clients(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    db = get_db()

    rows = db.execute(
        """
        SELECT id,name,protocol,link,token,created_at
        FROM clients
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return [dict(row) for row in rows]


@app.post("/api/clients")
async def add_client(
    request: Request,
    name: str = Form(...),
    link: str = Form(...),
):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    name = name.strip()
    link = link.strip()

    if not name:
        return JSONResponse(
            {"error": "نام کاربر خالی است"},
            status_code=400,
        )

    if not link:
        return JSONResponse(
            {"error": "لینک کانفیگ خالی است"},
            status_code=400,
        )

    protocol = detect_protocol(link)
    token = secrets.token_urlsafe(18)

    db = get_db()

    db.execute(
        """
        INSERT INTO clients
        (name,protocol,link,token)
        VALUES (?,?,?,?)
        """,
        (
            name,
            protocol,
            link,
            token,
        ),
    )

    db.commit()
    db.close()

    return {
        "ok": True,
        "name": name,
        "protocol": protocol,
        "token": token,
    }


@app.delete("/api/clients/{client_id}")
async def delete_client(
    request: Request,
    client_id: int,
):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    db = get_db()

    cur = db.execute(
        "DELETE FROM clients WHERE id=?",
        (client_id,),
    )

    db.commit()
    db.close()

    return {
        "ok": cur.rowcount > 0
    }


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.get("/sub/{token}")
async def subscription(token: str):

    db = get_db()

    rows = db.execute(
        """
        SELECT link
        FROM clients
        WHERE token=?
        """,
        (token,),
    ).fetchall()

    db.close()

    if not rows:
        return PlainTextResponse(
            "Subscription not found",
            status_code=404,
        )

    return PlainTextResponse(
        "\n".join(
            row["link"]
            for row in rows
        ),
        media_type="text/plain",
    )


# =========================================================
# TELEGRAM
# =========================================================

@app.get("/api/bots")
async def list_bots(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    db = get_db()

    rows = db.execute(
        """
        SELECT id,name,username,active,created_at
        FROM bots
        ORDER BY id DESC
        """
    ).fetchall()

    db.close()

    return [dict(row) for row in rows]


@app.post("/api/bots/check")
async def check_bot(
    request: Request,
    token: str = Form(...),
):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    token = token.strip()

    if not token:
        return JSONResponse(
            {"error": "Bot Token خالی است"},
            status_code=400,
        )

    try:

        async with httpx.AsyncClient(
            timeout=10
        ) as client:

            response = await client.get(
                f"https://api.telegram.org/bot{token}/getMe"
            )

        data = response.json()

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
        }

    if not data.get("ok"):
        return {
            "ok": False,
            "error": "Telegram token معتبر نیست",
            "telegram": data,
        }

    bot = data.get("result", {})

    username = bot.get(
        "username",
        "",
    )

    first_name = bot.get(
        "first_name",
        "Telegram Bot",
    )

    db = get_db()

    db.execute(
        """
        INSERT INTO bots
        (name,token,username,active)
        VALUES (?,?,?,1)
        """,
        (
            first_name,
            token,
            username,
        ),
    )

    db.commit()
    db.close()

    return {
        "ok": True,
        "name": first_name,
        "username": username,
    }


# =========================================================
# CLOUDFLARE
# =========================================================

@app.get("/api/cloudflare")
async def cloudflare(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    token = os.getenv(
        "CLOUDFLARE_API_TOKEN",
        "",
    )

    if not token:
        return {
            "configured": False,
            "status": "token not configured",
        }

    try:

        async with httpx.AsyncClient(
            timeout=10
        ) as client:

            response = await client.get(
                "https://api.cloudflare.com/client/v4/user/tokens/verify",
                headers={
                    "Authorization":
                    f"Bearer {token}"
                },
            )

        return response.json()

    except Exception as exc:

        return {
            "configured": True,
            "ok": False,
            "error": str(exc),
        }


# =========================================================
# GITHUB
# =========================================================

@app.get("/api/github")
async def github(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    token = os.getenv(
        "GITHUB_TOKEN",
        "",
    )

    if not token:
        return {
            "configured": False,
            "status": "token not configured",
        }

    try:

        async with httpx.AsyncClient(
            timeout=10
        ) as client:

            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization":
                    f"Bearer {token}",
                    "Accept":
                    "application/vnd.github+json",
                },
            )

        data = response.json()

        return {
            "configured": True,
            "ok": response.is_success,
            "login": data.get("login"),
        }

    except Exception as exc:

        return {
            "configured": True,
            "ok": False,
            "error": str(exc),
        }


# =========================================================
# RAILWAY
# =========================================================

@app.get("/api/railway")
async def railway(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    return {
        "platform": "Railway",
        "runtime": "Python / FastAPI",
        "status": "running",
        "version": VERSION,
    }


# =========================================================
# CONFIG
# =========================================================

@app.get("/api/config")
async def config(request: Request):

    if not is_logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401,
        )

    return {
        "brand": BRAND,
        "version": VERSION,
        "author": AUTHOR,
        "username": PANEL_USERNAME,
        "runtime": "Python / FastAPI",
        "railway": True,
        "protocols": [
            "VLESS",
            "VMESS",
            "Trojan",
            "Shadowsocks",
            "Hysteria2",
            "TUIC",
        ],
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
                "8080",
            )
        ),
    )
