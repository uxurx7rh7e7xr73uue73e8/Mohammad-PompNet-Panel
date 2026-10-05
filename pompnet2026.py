import os
import io
import re
import time
import secrets
import sqlite3
import platform
import subprocess
from pathlib import Path

import httpx
import qrcode

from fastapi import FastAPI, Request, Form
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse
)
from starlette.middleware.sessions import SessionMiddleware


BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "pompnet2026.db"

VERSION = "2026.10.05"
BRAND = "MR:Mohammad Pomp Net"
AUTHOR = "کدنویسی شده توسط تیم PompNet"

ADMIN_PASSWORD = os.getenv(
    "POMPNET_ADMIN_PASSWORD",
    "Mohammad@2026"
)

SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    "POMP_NET_CHANGE_THIS_SECRET"
)

app = FastAPI(
    title=BRAND,
    version=VERSION
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=604800,
    same_site="lax",
    https_only=False
)


# =========================================================
# DATABASE
# =========================================================

def database():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():

    conn = database()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        username TEXT DEFAULT '',
        protocol TEXT NOT NULL,
        link TEXT NOT NULL,
        token TEXT UNIQUE NOT NULL,
        volume INTEGER DEFAULT 0,
        days INTEGER DEFAULT 30,
        expire_at TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS bots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        token TEXT NOT NULL,
        username TEXT DEFAULT '',
        bot_id TEXT DEFAULT '',
        status TEXT DEFAULT 'unknown',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# HELPERS
# =========================================================

def is_logged(request: Request):
    return request.session.get("admin") is True


def log_action(action, details=""):

    conn = database()

    conn.execute(
        """
        INSERT INTO logs(action, details)
        VALUES(?, ?)
        """,
        (action, details)
    )

    conn.commit()
    conn.close()


def detect_protocol(link):

    link = link.strip().lower()

    protocols = {
        "vless://": "VLESS",
        "vmess://": "VMESS",
        "trojan://": "TROJAN",
        "ss://": "SHADOWSOCKS",
        "hysteria2://": "HYSTERIA2",
        "hy2://": "HYSTERIA2",
        "tuic://": "TUIC"
    }

    for prefix, name in protocols.items():

        if link.startswith(prefix):
            return name

    return "UNKNOWN"


def new_token():
    return secrets.token_urlsafe(32)


def ui():

    file = BASE_DIR / "pompnet_ui2026.html"

    if not file.exists():

        return """
        <h1>خطای PompNet</h1>
        <p>فایل pompnet_ui2026.html پیدا نشد.</p>
        """

    return file.read_text(
        encoding="utf-8"
    )


# =========================================================
# LOGIN
# =========================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):

    if is_logged(request):
        return RedirectResponse(
            "/",
            status_code=303
        )

    return HTMLResponse("""
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>ورود | PompNet</title>

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

font-family:Tahoma,Arial;

background:
radial-gradient(
circle at 50% 0%,
#32147b,
transparent 38%
),
radial-gradient(
circle at 10% 90%,
#082a63,
transparent 35%
),
#03030a;

color:white;
overflow:hidden;
}

body:before{
content:"";
position:fixed;
inset:-50%;

background:
conic-gradient(
transparent,
rgba(126,54,255,.12),
transparent,
rgba(0,180,255,.10),
transparent
);

animation:spin 12s linear infinite;
}

@keyframes spin{
to{
transform:rotate(360deg);
}
}

.login{
position:relative;
width:min(420px,92%);

padding:35px;

border-radius:30px;

background:
rgba(10,8,25,.82);

border:
1px solid rgba(135,75,255,.45);

box-shadow:
0 0 80px rgba(95,45,255,.25);

backdrop-filter:blur(25px);

text-align:center;
}

.logo{
width:105px;
height:105px;

margin:0 auto 20px;

border-radius:50%;

display:flex;
align-items:center;
justify-content:center;

background:
linear-gradient(
135deg,
#6638ff,
#00aaff
);

box-shadow:
0 0 40px rgba(100,60,255,.6);

font-size:28px;
font-weight:900;
}

h1{
margin:0;
font-size:25px;
}

p{
color:#aaa;
}

input{
width:100%;
padding:15px;

border-radius:14px;

border:
1px solid #3b2772;

background:#070711;

color:white;

outline:none;

margin:15px 0;
}

button{
width:100%;

padding:15px;

border:0;

border-radius:14px;

background:
linear-gradient(
90deg,
#6030ff,
#a335e8
);

color:white;

font-weight:900;

cursor:pointer;
}

.footer{
margin-top:20px;
font-size:11px;
color:#777;
}

</style>
</head>

<body>

<div class="login">

<div class="logo">
PN
</div>

<h1>
MR:Mohammad Pomp Net
</h1>

<p>
پنل مدیریت حرفه‌ای PompNet
</p>

<form method="post">

<input
type="password"
name="password"
placeholder="رمز مدیریت"
required
>

<button>
🚀 ورود به پنل
</button>

</form>

<div class="footer">
کدنویسی شده توسط تیم PompNet
</div>

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

        log_action(
            "LOGIN",
            "ورود موفق مدیر"
        )

        return RedirectResponse(
            "/",
            status_code=303
        )

    return HTMLResponse(
        """
        <div style="
        background:#05050b;
        color:white;
        font-family:Tahoma;
        text-align:center;
        padding:80px">
        <h2>❌ رمز عبور اشتباه است</h2>
        <a href="/login">بازگشت</a>
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
# MAIN
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    if not is_logged(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    return HTMLResponse(ui())


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "online",
        "brand": BRAND,
        "version": VERSION,
        "engine": "Python FastAPI",
        "author": AUTHOR
    }


# =========================================================
# OVERVIEW
# =========================================================

@app.get("/api/overview")
async def overview(request: Request):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = database()

    clients = conn.execute(
        "SELECT COUNT(*) c FROM clients"
    ).fetchone()["c"]

    bots = conn.execute(
        "SELECT COUNT(*) c FROM bots"
    ).fetchone()["c"]

    logs = conn.execute(
        "SELECT COUNT(*) c FROM logs"
    ).fetchone()["c"]

    conn.close()

    return {
        "brand": BRAND,
        "version": VERSION,
        "clients": clients,
        "bots": bots,
        "logs": logs,
        "status": "online"
    }


# =========================================================
# SYSTEM
# =========================================================

@app.get("/api/system")
async def system_info(request: Request):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    memory = "N/A"

    try:

        result = subprocess.check_output(
            [
                "sh",
                "-c",
                "free -m | awk 'NR==2{print $3\"/\"$2\" MB\"}'"
            ],
            text=True
        ).strip()

        memory = result

    except Exception:
        pass

    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "memory": memory,
        "hostname": platform.node()
    }


# =========================================================
# CLIENTS
# =========================================================

@app.get("/api/clients")
async def clients(request: Request):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = database()

    rows = conn.execute("""
    SELECT *
    FROM clients
    ORDER BY id DESC
    """).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


@app.post("/api/clients")
async def create_client(
    request: Request,
    name: str = Form(...),
    username: str = Form(""),
    link: str = Form(...),
    volume: int = Form(0),
    days: int = Form(30),
    expire_at: str = Form("")
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    protocol = detect_protocol(link)

    if protocol == "UNKNOWN":

        return JSONResponse(
            {
                "error":
                "لینک معتبر VLESS / VMESS / Trojan / SS / Hysteria2 / TUIC وارد کنید."
            },
            status_code=400
        )

    token = new_token()

    conn = database()

    conn.execute(
        """
        INSERT INTO clients
        (
            name,
            username,
            protocol,
            link,
            token,
            volume,
            days,
            expire_at
        )
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            name.strip(),
            username.strip(),
            protocol,
            link.strip(),
            token,
            volume,
            days,
            expire_at.strip()
        )
    )

    conn.commit()
    conn.close()

    log_action(
        "CLIENT_CREATE",
        f"{name} / {protocol}"
    )

    return {
        "success": True,
        "protocol": protocol,
        "token": token,
        "subscription":
            f"/sub/{token}"
    }


@app.delete("/api/clients/{client_id}")
async def remove_client(
    request: Request,
    client_id: int
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = database()

    row = conn.execute(
        "SELECT name FROM clients WHERE id=?",
        (client_id,)
    ).fetchone()

    conn.execute(
        "DELETE FROM clients WHERE id=?",
        (client_id,)
    )

    conn.commit()
    conn.close()

    log_action(
        "CLIENT_DELETE",
        str(row["name"] if row else client_id)
    )

    return {
        "success": True
    }


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.get("/sub/{token}")
async def subscription(token: str):

    conn = database()

    row = conn.execute(
        """
        SELECT link
        FROM clients
        WHERE token=?
        """,
        (token,)
    ).fetchone()

    conn.close()

    if not row:

        return PlainTextResponse(
            "Subscription not found",
            status_code=404
        )

    return PlainTextResponse(
        row["link"],
        media_type="text/plain"
    )


# =========================================================
# QR
# =========================================================

@app.get("/api/qr")
async def qr(
    request: Request,
    data: str
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    image = qrcode.make(data)

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG"
    )

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png"
    )


# =========================================================
# TELEGRAM
# =========================================================

@app.get("/api/bots")
async def bots(request: Request):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = database()

    rows = conn.execute(
        """
        SELECT
        id,
        name,
        username,
        bot_id,
        status,
        created_at
        FROM bots
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


@app.post("/api/bots/check")
async def bot_check(
    request: Request,
    token: str = Form(...)
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = token.strip()

    if not re.match(
        r"^\d+:[A-Za-z0-9_-]+$",
        token
    ):

        return JSONResponse(
            {
                "success": False,
                "error": "فرمت Bot Token اشتباه است."
            },
            status_code=400
        )

    url = (
        "https://api.telegram.org/"
        f"bot{token}/getMe"
    )

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(url)

        data = response.json()

        if not data.get("ok"):

            return {
                "success": False,
                "error": "Bot Token معتبر نیست."
            }

        bot = data["result"]

        conn = database()

        conn.execute(
            """
            INSERT INTO bots
            (
                name,
                token,
                username,
                bot_id,
                status
            )
            VALUES(?,?,?,?,?)
            """,
            (
                bot.get("first_name")
                or bot.get("username")
                or "PompNet Bot",

                token,

                bot.get(
                    "username",
                    ""
                ),

                str(
                    bot.get(
                        "id",
                        ""
                    )
                ),

                "online"
            )
        )

        conn.commit()
        conn.close()

        log_action(
            "TELEGRAM_BOT",
            bot.get("username", "")
        )

        return {
            "success": True,
            "id": bot.get("id"),
            "username": bot.get("username"),
            "name": bot.get("first_name")
        }

    except Exception as exc:

        return {
            "success": False,
            "error": str(exc)
        }


# =========================================================
# TELEGRAM BOT INFO
# =========================================================

@app.get("/api/telegram/config")
async def telegram_config(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = os.getenv(
        "TELEGRAM_BOT_TOKEN",
        ""
    )

    return {
        "configured": bool(token)
    }


# =========================================================
# CLOUDFLARE
# =========================================================

@app.get("/api/cloudflare")
async def cloudflare(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = os.getenv(
        "CLOUDFLARE_API_TOKEN",
        ""
    )

    zone = os.getenv(
        "CLOUDFLARE_ZONE_ID",
        ""
    )

    if not token:

        return {
            "configured": False,
            "message":
            "CLOUDFLARE_API_TOKEN تنظیم نشده است."
        }

    headers = {
        "Authorization":
            f"Bearer {token}"
    }

    try:

        url = (
            f"https://api.cloudflare.com/"
            f"client/v4/zones/{zone}"
        )

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                url,
                headers=headers
            )

        return response.json()

    except Exception as exc:

        return {
            "success": False,
            "error": str(exc)
        }


# =========================================================
# GITHUB
# =========================================================

@app.get("/api/github")
async def github(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    token = os.getenv(
        "GITHUB_TOKEN",
        ""
    )

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
        "Authorization":
            f"Bearer {token}",
        "Accept":
            "application/vnd.github+json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.get(
                f"https://api.github.com/repos/{repo}",
                headers=headers
            )

        return {
            "configured": True,
            "success": response.is_success,
            "repository": repo,
            "data": response.json()
        }

    except Exception as exc:

        return {
            "success": False,
            "error": str(exc)
        }


# =========================================================
# RAILWAY
# =========================================================

@app.get("/api/railway")
async def railway(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    return {
        "platform": "Railway",
        "runtime": "Python FastAPI",
        "configured":
            bool(
                os.getenv(
                    "RAILWAY_TOKEN"
                )
            ),
        "port":
            os.getenv(
                "PORT",
                "8080"
            ),
        "status": "ready"
    }


# =========================================================
# X-UI / SANAEI CONFIG
# =========================================================

@app.get("/api/xui")
async def xui_status(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    return {
        "configured":
            bool(
                os.getenv(
                    "XUI_URL"
                )
            ),
        "url":
            os.getenv(
                "XUI_URL",
                ""
            ),
        "username":
            os.getenv(
                "XUI_USERNAME",
                ""
            ),
        "message":
            "اتصال Sanaei/X-UI با API واقعی آماده تنظیم است."
    }


# =========================================================
# LOGS
# =========================================================

@app.get("/api/logs")
async def logs(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    conn = database()

    rows = conn.execute(
        """
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 100
        """
    ).fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# CONFIG
# =========================================================

@app.get("/api/config")
async def config(
    request: Request
):

    if not is_logged(request):

        return JSONResponse(
            {"error": "unauthorized"},
            status_code=401
        )

    return {
        "brand": BRAND,
        "version": VERSION,
        "author": AUTHOR,

        "protocols": [
            "VLESS",
            "VMESS",
            "TROJAN",
            "SHADOWSOCKS",
            "HYSTERIA2",
            "TUIC"
        ],

        "cloudflare":
            bool(
                os.getenv(
                    "CLOUDFLARE_API_TOKEN"
                )
            ),

        "github":
            bool(
                os.getenv(
                    "GITHUB_TOKEN"
                )
            ),

        "railway":
            bool(
                os.getenv(
                    "RAILWAY_TOKEN"
                )
            ),

        "xui":
            bool(
                os.getenv(
                    "XUI_URL"
                )
            )
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
