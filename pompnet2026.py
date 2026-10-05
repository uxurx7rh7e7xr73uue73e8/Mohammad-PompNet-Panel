import os
import re
import json
import secrets
import sqlite3
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware


APP_DIR = Path(__file__).resolve().parent
DB_FILE = APP_DIR / "pompnet2026.db"

VERSION = "2026.10.05"
BRAND = "MR:Mohammad Pomp Net"

ADMIN_PASSWORD = os.getenv("POMPNET_ADMIN_PASSWORD", "Mohammad@2026")
SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    "change-this-secret-in-railway"
)

app = FastAPI(
    title=BRAND,
    version=VERSION
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=True
)


# =========================
# DATABASE
# =========================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            protocol TEXT NOT NULL,
            link TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            username TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# HELPERS
# =========================

def logged_in(request: Request):
    return request.session.get("admin") is True


def detect_protocol(link: str):
    value = link.lower().strip()

    if value.startswith("vless://"):
        return "VLESS"

    if value.startswith("vmess://"):
        return "VMESS"

    if value.startswith("trojan://"):
        return "TROJAN"

    if value.startswith("ss://"):
        return "SHADOWSOCKS"

    if value.startswith("hysteria2://"):
        return "HYSTERIA2"

    if value.startswith("hy2://"):
        return "HYSTERIA2"

    if value.startswith("tuic://"):
        return "TUIC"

    return "UNKNOWN"


def make_token():
    return secrets.token_urlsafe(24)


def page_html():
    file = APP_DIR / "pompnet_ui2026.html"

    if not file.exists():
        return """
        <h1>خطا</h1>
        <p>فایل pompnet_ui2026.html پیدا نشد.</p>
        """

    return file.read_text(encoding="utf-8")


# =========================
# LOGIN
# =========================

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ورود | Mohammad PompNet</title>
<style>
body{
    margin:0;
    min-height:100vh;
    display:flex;
    align-items:center;
    justify-content:center;
    background:
    radial-gradient(circle at top,#25104d,#070711 55%,#020207);
    font-family:Tahoma,sans-serif;
    color:white;
}
.box{
    width:min(420px,90%);
    padding:30px;
    border:1px solid #693cff;
    border-radius:25px;
    background:rgba(15,10,30,.85);
    box-shadow:0 0 50px rgba(110,50,255,.25);
}
h1{
    text-align:center;
}
input{
    width:100%;
    box-sizing:border-box;
    padding:15px;
    margin:15px 0;
    border-radius:14px;
    border:1px solid #613cff;
    background:#090914;
    color:white;
}
button{
    width:100%;
    padding:15px;
    border:0;
    border-radius:14px;
    background:linear-gradient(90deg,#6b35ff,#a23cff);
    color:white;
    font-weight:bold;
    cursor:pointer;
}
</style>
</head>
<body>
<div class="box">
<h1>🚀 Mohammad PompNet</h1>
<p style="text-align:center">ورود مدیریت پنل</p>

<form method="post">
<input
    type="password"
    name="password"
    placeholder="رمز مدیریت"
    required
>
<button type="submit">ورود به پنل</button>
</form>

</div>
</body>
</html>
"""


@app.post("/login")
async def login(password: str = Form(...)):
    if secrets.compare_digest(password, ADMIN_PASSWORD):
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            "pompnet_login",
            "1",
            httponly=True,
            secure=True,
            samesite="lax"
        )
        return response

    return HTMLResponse(
        "<h2 style='text-align:center'>رمز ورود اشتباه است.</h2>",
        status_code=401
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("pompnet_login")

    return response


# =========================
# MAIN PANEL
# =========================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)

    return HTMLResponse(page_html())


# =========================
# HEALTH
# =========================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "panel": BRAND,
        "version": VERSION
    }


# =========================
# OVERVIEW
# =========================

@app.get("/api/overview")
async def overview(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = db()

    clients = conn.execute(
        "SELECT COUNT(*) AS count FROM clients"
    ).fetchone()["count"]

    bots = conn.execute(
        "SELECT COUNT(*) AS count FROM bots"
    ).fetchone()["count"]

    conn.close()

    return {
        "brand": BRAND,
        "version": VERSION,
        "clients": clients,
        "bots": bots,
        "database": "SQLite",
        "status": "online"
    }


# =========================
# VPN CLIENTS
# =========================

@app.get("/api/clients")
async def get_clients(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = db()

    rows = conn.execute("""
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

    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/clients")
async def add_client(
    request: Request,
    name: str = Form(...),
    link: str = Form(...)
):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    name = name.strip()
    link = link.strip()

    if not name or not link:
        return JSONResponse(
            {"error": "نام و لینک الزامی است."},
            status_code=400
        )

    protocol = detect_protocol(link)

    if protocol == "UNKNOWN":
        return JSONResponse(
            {"error": "فرمت لینک پشتیبانی نمی‌شود."},
            status_code=400
        )

    token = make_token()

    conn = db()

    conn.execute("""
        INSERT INTO clients
        (name, protocol, link, token)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        protocol,
        link,
        token
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "name": name,
        "protocol": protocol,
        "token": token,
        "subscription": f"/sub/{token}"
    }


@app.delete("/api/clients/{client_id}")
async def delete_client(
    request: Request,
    client_id: int
):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = db()

    conn.execute(
        "DELETE FROM clients WHERE id=?",
        (client_id,)
    )

    conn.commit()
    conn.close()

    return {
        "success": True
    }


# =========================
# SUBSCRIPTION
# =========================

@app.get("/sub/{token}")
async def subscription(token: str):

    conn = db()

    rows = conn.execute("""
        SELECT link
        FROM clients
        WHERE token=?
    """, (token,)).fetchall()

    conn.close()

    if not rows:
        return PlainTextResponse(
            "Subscription not found",
            status_code=404
        )

    links = [
        row["link"]
        for row in rows
    ]

    return PlainTextResponse(
        "\n".join(links),
        media_type="text/plain"
    )


# =========================
# TELEGRAM
# =========================

@app.get("/api/bots")
async def get_bots(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = db()

    rows = conn.execute("""
        SELECT id,name,username,active,created_at
        FROM bots
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/bots/check")
async def check_bot(
    request: Request,
    token: str = Form(...)
):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = token.strip()

    if not token:
        return JSONResponse(
            {"error": "Bot Token خالی است."},
            status_code=400
        )

    url = f"https://api.telegram.org/bot{token}/getMe"

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(url)

        data = response.json()

        if not data.get("ok"):
            return JSONResponse(
                {
                    "valid": False,
                    "error": "Bot Token معتبر نیست."
                },
                status_code=400
            )

        bot = data["result"]

        conn = db()

        conn.execute("""
            INSERT INTO bots
            (name, token, username, active)
            VALUES (?, ?, ?, 1)
        """, (
            bot.get("first_name") or bot.get("username") or "Telegram Bot",
            token,
            bot.get("username", "")
        ))

        conn.commit()
        conn.close()

        return {
            "valid": True,
            "id": bot.get("id"),
            "name": bot.get("first_name"),
            "username": bot.get("username")
        }

    except Exception as exc:

        return JSONResponse(
            {
                "valid": False,
                "error": str(exc)
            },
            status_code=500
        )


# =========================
# CLOUDFLARE
# =========================

@app.get("/api/cloudflare")
async def cloudflare_status(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = os.getenv("CLOUDFLARE_API_TOKEN")
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID")

    if not token or not zone_id:
        return {
            "configured": False,
            "message": "Cloudflare variables تنظیم نشده‌اند."
        }

    try:

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}"

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                url,
                headers=headers
            )

        data = response.json()

        return {
            "configured": True,
            "success": data.get("success", False),
            "zone": data.get("result", {})
        }

    except Exception as exc:

        return {
            "configured": True,
            "success": False,
            "error": str(exc)
        }


# =========================
# GITHUB
# =========================

@app.get("/api/github")
async def github_status(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv(
        "GITHUB_REPO",
        "uxurx7rh7e7xr73uue73e8/Mohammad-PompNet-Panel"
    )

    if not token:
        return {
            "configured": False,
            "repository": repo
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                f"https://api.github.com/repos/{repo}",
                headers=headers
            )

        data = response.json()

        return {
            "configured": True,
            "success": response.is_success,
            "repository": repo,
            "private": data.get("private"),
            "default_branch": data.get("default_branch")
        }

    except Exception as exc:

        return {
            "configured": True,
            "success": False,
            "error": str(exc)
        }


# =========================
# RAILWAY
# =========================

@app.get("/api/railway")
async def railway_status(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    return {
        "platform": "Railway",
        "configured": bool(os.getenv("RAILWAY_TOKEN")),
        "port": os.getenv("PORT", "8080"),
        "runtime": "Python / FastAPI",
        "status": "ready"
    }


# =========================
# CONFIG
# =========================

@app.get("/api/config")
async def config(request: Request):

    if not logged_in(request):
        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    return {
        "brand": BRAND,
        "version": VERSION,
        "protocols": [
            "VLESS",
            "VMESS",
            "TROJAN",
            "SHADOWSOCKS",
            "HYSTERIA2",
            "TUIC"
        ],
        "telegram": bool(
            os.getenv("TELEGRAM_BOT_TOKEN")
        ),
        "cloudflare": bool(
            os.getenv("CLOUDFLARE_API_TOKEN")
        ),
        "github": bool(
            os.getenv("GITHUB_TOKEN")
        ),
        "railway": bool(
            os.getenv("RAILWAY_TOKEN")
        )
    }


# =========================
# SUPPORT
# =========================

@app.get("/api/support")
async def support():

    return {
        "telegram": "https://t.me/NovaTunneli",
        "group": "https://t.me/PompNett",
        "whatsapp": "https://wa.me/message/LRTDKAYCT6IMN1"
    }


# =========================
# START
# =========================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "pompnet2026:app",
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "8080")
        )
    )
