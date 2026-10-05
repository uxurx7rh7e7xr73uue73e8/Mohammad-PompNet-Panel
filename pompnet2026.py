import os
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from starlette.middleware.sessions import SessionMiddleware


# =========================================================
# POMP NET CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "pompnet2026.db"

BRAND = "MR:Mohammad Pomp Net"
VERSION = "2026.10.05"

# یوزرنیم و پسورد پیش‌فرض پنل
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
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


init_database()


# =========================================================
# AUTH
# =========================================================

def is_logged_in(request: Request) -> bool:
    return request.session.get("pompnet_admin") is True


def login_page(error=""):

    error_html = ""

    if error:
        error_html = f"""
        <div class="error">
            {error}
        </div>
        """

    return f"""
<!DOCTYPE html>

<html lang="fa" dir="rtl">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
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

    align-items:center;

    justify-content:center;

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

.login-box {{

    width:min(440px,100%);

    padding:30px;

    border-radius:28px;

    background:
        rgba(12,10,25,.88);

    border:
        1px solid
        rgba(130,80,255,.45);

    box-shadow:
        0 25px 80px
        rgba(0,0,0,.55),
        0 0 50px
        rgba(100,40,255,.12);

    backdrop-filter:blur(20px);
}}

.logo {{

    text-align:center;

    font-size:25px;

    font-weight:900;

    margin-bottom:8px;
}}

.subtitle {{

    text-align:center;

    color:#aaa;

    margin-bottom:25px;

    line-height:2;
}}

.field {{

    margin-bottom:16px;
}}

label {{

    display:block;

    color:#bdb5d1;

    font-size:13px;

    margin-bottom:7px;
}}

input {{

    width:100%;

    padding:15px;

    border-radius:14px;

    border:
        1px solid
        #38275f;

    background:#080710;

    color:#fff;

    outline:none;

    font-size:15px;
}}

input:focus {{

    border-color:#824cff;

    box-shadow:
        0 0 20px
        rgba(120,60,255,.15);
}}

button {{

    width:100%;

    border:0;

    padding:15px;

    border-radius:14px;

    color:#fff;

    font-size:15px;

    font-weight:900;

    cursor:pointer;

    background:
        linear-gradient(
            90deg,
            #5526e8,
            #9c35df
        );

    box-shadow:
        0 10px 30px
        rgba(100,40,230,.2);
}}

.error {{

    padding:12px;

    margin-bottom:16px;

    border-radius:12px;

    text-align:center;

    color:#ff9aae;

    background:#32121e;

    border:1px solid #65263a;
}}

.footer {{

    margin-top:20px;

    text-align:center;

    color:#777;

    font-size:11px;
}}

</style>

</head>

<body>

<div class="login-box">

<div class="logo">
🚀 MR:Mohammad Pomp Net
</div>

<div class="subtitle">
ورود به پنل مدیریت<br>
نسخه {VERSION}
</div>

{error_html}

<form
    method="post"
    action="/login"
>

<div class="field">

<label>
نام کاربری
</label>

<input
    type="text"
    name="username"
    placeholder="نام کاربری"
    autocomplete="username"
    required
>

</div>


<div class="field">

<label>
رمز عبور
</label>

<input
    type="password"
    name="password"
    placeholder="رمز عبور"
    autocomplete="current-password"
    required
>

</div>


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

    username_ok = secrets.compare_digest(
        username,
        PANEL_USERNAME
    )

    password_ok = secrets.compare_digest(
        password,
        PANEL_PASSWORD
    )

    if username_ok and password_ok:

        request.session.clear()

        request.session["pompnet_admin"] = True

        request.session["username"] = username

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
async def logout(request: Request):

    request.session.clear()

    return RedirectResponse(
        "/login",
        status_code=303
    )


# =========================================================
# MAIN PANEL
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    if not is_logged_in(request):

        return RedirectResponse(
            "/login",
            status_code=303
        )

    ui_file = BASE_DIR / "pompnet_ui2026.html"

    if not ui_file.exists():

        return HTMLResponse(
            """
            <h2>
            فایل pompnet_ui2026.html پیدا نشد.
            </h2>
            """,
            status_code=500
        )

    html = ui_file.read_text(
        encoding="utf-8"
    )

    return HTMLResponse(
        html
    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "ok",
        "panel": BRAND,
        "version": VERSION
    }


# =========================================================
# OVERVIEW
# =========================================================

@app.get("/api/overview")
async def overview(request: Request):

    if not is_logged_in(request):

        return JSONResponse(
            {
                "error": "unauthorized"
            },
            status_code=401
        )

    connection = get_db()

    clients = connection.execute(
        "SELECT COUNT(*) AS count FROM clients"
    ).fetchone()["count"]

    bots = connection.execute(
        "SELECT COUNT(*) AS count FROM bots"
    ).fetchone()["count"]

    connection.close()

    return {
        "brand": BRAND,
        "version": VERSION,
        "clients": clients,
        "bots": bots,
        "status": "online"
    }


# =========================================================
# CLIENTS
# =========================================================

@app.get("/api/clients")
async def clients(request: Request):

    if not is_logged_in(request):

        return JSONResponse(
            {
                "error": "unauthorized"
            },
            status_code=401
        )

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

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# SUBSCRIPTION
# =========================================================

@app.get("/sub/{token}")
async def subscription(token: str):

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

    links = [
        row["link"]
        for row in rows
    ]

    return PlainTextResponse(
        "\n".join(links),
        media_type="text/plain"
    )


# =========================================================
# CONFIG
# =========================================================

@app.get("/api/config")
async def config(request: Request):

    if not is_logged_in(request):

        return JSONResponse(
            {
                "error": "unauthorized"
            },
            status_code=401
        )

    return {

        "brand": BRAND,

        "version": VERSION,

        "username": PANEL_USERNAME,

        "protocols": [
            "VLESS",
            "VMESS",
            "Trojan",
            "Shadowsocks",
            "Hysteria2",
            "TUIC"
        ],

        "runtime": "Python / FastAPI",

        "railway": True

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
