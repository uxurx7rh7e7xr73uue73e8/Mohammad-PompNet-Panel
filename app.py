import os
import secrets
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles


BASE = Path(__file__).resolve().parent
DB = BASE / "pompnet.db"

app = FastAPI(title="PompNet Panel", version="2026.10.05")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("POMPNET_SESSION_SECRET", secrets.token_hex(32)),
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")


ADMIN_USER = os.getenv("POMPNET_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("POMPNET_ADMIN_PASSWORD", "change-me-now")

XUI_URL = os.getenv("XUI_URL", "").rstrip("/")
XUI_USER = os.getenv("XUI_USER", "")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "")
XUI_TOKEN = os.getenv("XUI_TOKEN", "")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CF_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_ZONE = os.getenv("CLOUDFLARE_ZONE_ID", "")

POMPNET_NAME = "MR:Mohammad Pomp Net"
POMPNET_VERSION = "2026.10.05"


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()

    con.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        protocol TEXT DEFAULT 'vless',
        node TEXT DEFAULT '',
        inbound_id INTEGER,
        uuid TEXT DEFAULT '',
        sub_token TEXT UNIQUE,
        total_gb REAL DEFAULT 0,
        expire_date TEXT DEFAULT '',
        enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        username TEXT DEFAULT '',
        enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.commit()
    con.close()


init_db()


def logged(request: Request):
    return request.session.get("admin") is True


def require_login(request: Request):
    if not logged(request):
        raise HTTPException(401, "ورود لازم است")


def log(action):
    con = db()
    con.execute("INSERT INTO logs(action) VALUES(?)", (action,))
    con.commit()
    con.close()


async def xui_request(method, path, **kwargs):
    if not XUI_URL:
        raise RuntimeError("XUI_URL تنظیم نشده است")

    headers = kwargs.pop("headers", {})

    if XUI_TOKEN:
        headers["Authorization"] = f"Bearer {XUI_TOKEN}"

    timeout = httpx.Timeout(20)

    async with httpx.AsyncClient(
        timeout=timeout,
        verify=False,
        follow_redirects=True,
    ) as client:

        if XUI_TOKEN:
            r = await client.request(
                method,
                XUI_URL + path,
                headers=headers,
                **kwargs
            )
        else:
            login = await client.post(
                XUI_URL + "/login",
                data={
                    "username": XUI_USER,
                    "password": XUI_PASSWORD,
                },
            )

            if login.status_code >= 400:
                raise RuntimeError("ورود به Sanaei/X-UI ناموفق بود")

            r = await client.request(
                method,
                XUI_URL + path,
                headers=headers,
                **kwargs
            )

        r.raise_for_status()
        return r.json()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if not logged(request):
        return RedirectResponse("/login")

    html = (BASE / "templates" / "panel.html").read_text(
        encoding="utf-8"
    )

    return HTMLResponse(html)


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    html = (BASE / "templates" / "panel.html").read_text(
        encoding="utf-8"
    )
    return HTMLResponse(html)


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):

    if secrets.compare_digest(username, ADMIN_USER) and \
       secrets.compare_digest(password, ADMIN_PASSWORD):

        request.session["admin"] = True
        log("ورود موفق مدیر")
        return RedirectResponse("/", status_code=303)

    log("تلاش ورود ناموفق")
    return RedirectResponse("/login?error=1", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/api/overview")
async def overview(request: Request):

    require_login(request)

    con = db()

    clients = con.execute(
        "SELECT COUNT(*) FROM clients"
    ).fetchone()[0]

    nodes = con.execute(
        "SELECT COUNT(*) FROM nodes WHERE enabled=1"
    ).fetchone()[0]

    con.close()

    xui_status = False

    if XUI_URL:
        try:
            await xui_request("GET", "/panel/api/inbounds/list")
            xui_status = True
        except Exception:
            xui_status = False

    return {
        "name": POMPNET_NAME,
        "version": POMPNET_VERSION,
        "clients": clients,
        "nodes": nodes,
        "xui": xui_status,
        "telegram": bool(TELEGRAM_TOKEN),
        "cloudflare": bool(CF_TOKEN),
    }


@app.get("/api/inbounds")
async def inbounds(request: Request):

    require_login(request)

    try:
        data = await xui_request(
            "GET",
            "/panel/api/inbounds/list"
        )

        return data

    except Exception as e:
        return JSONResponse(
            {
                "success": False,
                "error": str(e),
                "items": []
            },
            status_code=503
        )


@app.get("/api/clients")
async def clients(request: Request):

    require_login(request)

    con = db()

    rows = con.execute(
        "SELECT * FROM clients ORDER BY id DESC"
    ).fetchall()

    con.close()

    return [dict(x) for x in rows]


@app.post("/api/clients")
async def create_client(request: Request):

    require_login(request)

    body = await request.json()

    name = body.get("name", "").strip()
    email = body.get("email", "").strip()
    protocol = body.get("protocol", "vless").lower()
    node = body.get("node", "")
    inbound_id = body.get("inbound_id")

    if not name or not email:
        raise HTTPException(
            400,
            "نام و ایمیل الزامی است"
        )

    client_uuid = str(uuid.uuid4())

    sub_token = secrets.token_urlsafe(32)

    con = db()

    try:
        con.execute(
            """
            INSERT INTO clients
            (name,email,protocol,node,inbound_id,uuid,sub_token,
             total_gb,expire_date,enabled)
            VALUES(?,?,?,?,?,?,?,?,?,1)
            """,
            (
                name,
                email,
                protocol,
                node,
                inbound_id,
                client_uuid,
                sub_token,
                float(body.get("total_gb", 0)),
                body.get("expire_date", ""),
            ),
        )

        con.commit()

    except sqlite3.IntegrityError:
        con.close()
        raise HTTPException(
            409,
            "این ایمیل قبلاً ثبت شده است"
        )

    con.close()

    log(f"ساخت کاربر {email}")

    return {
        "success": True,
        "uuid": client_uuid,
        "subscription":
            f"/sub/{sub_token}"
    }


@app.delete("/api/clients/{client_id}")
async def delete_client(
    client_id: int,
    request: Request
):

    require_login(request)

    con = db()

    row = con.execute(
        "SELECT email FROM clients WHERE id=?",
        (client_id,)
    ).fetchone()

    if not row:
        con.close()
        raise HTTPException(404, "کاربر پیدا نشد")

    con.execute(
        "DELETE FROM clients WHERE id=?",
        (client_id,)
    )

    con.commit()
    con.close()

    log(f"حذف کاربر {row['email']}")

    return {"success": True}


@app.get("/api/server/status")
async def server_status(request: Request):

    require_login(request)

    try:
        data = await xui_request(
            "GET",
            "/panel/api/server/status"
        )

        return {
            "success": True,
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/telegram")
async def telegram(request: Request):

    require_login(request)

    if not TELEGRAM_TOKEN:
        return {
            "success": False,
            "message": "TELEGRAM_BOT_TOKEN تنظیم نشده"
        }

    async with httpx.AsyncClient(timeout=15) as client:

        r = await client.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
        )

        data = r.json()

    return data


@app.get("/api/cloudflare")
async def cloudflare(request: Request):

    require_login(request)

    if not CF_TOKEN or not CF_ZONE:
        return {
            "success": False,
            "message": "Cloudflare variables تنظیم نشده"
        }

    headers = {
        "Authorization": f"Bearer {CF_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:

        r = await client.get(
            f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE}",
            headers=headers,
        )

    return r.json()


@app.get("/sub/{token}")
async def subscription(token: str):

    con = db()

    row = con.execute(
        "SELECT * FROM clients WHERE sub_token=? AND enabled=1",
        (token,)
    ).fetchone()

    con.close()

    if not row:
        raise HTTPException(
            404,
            "Subscription پیدا نشد"
        )

    # اگر لینک واقعی نود در آینده از Sanaei دریافت شود،
    # همین endpoint می‌تواند آن را خروجی دهد.
    # فعلاً اطلاعات داخلی پنل لو نمی‌رود.

    return {
        "name": row["name"],
        "protocol": row["protocol"],
        "uuid": row["uuid"],
        "expire": row["expire_date"],
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "panel": "PompNet",
        "version": POMPNET_VERSION
    }
