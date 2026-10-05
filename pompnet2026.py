import base64
import io
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import psutil
import qrcode

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from itsdangerous import URLSafeTimedSerializer

from sanaei_adapter import SanaeiAdapter


APP_NAME = "MR:Mohammad Pomp Net"
VERSION = "2026.10.05"

DB_FILE = os.getenv(
    "POMPNET_DB",
    "pompnet2026.db",
)

ADMIN_PASSWORD = os.getenv(
    "POMPNET_ADMIN_PASSWORD",
    "change-this-password",
)

SESSION_SECRET = os.getenv(
    "POMPNET_SESSION_SECRET",
    secrets.token_urlsafe(48),
)

XUI_URL = os.getenv("XUI_URL", "")
XUI_USERNAME = os.getenv("XUI_USERNAME", "")
XUI_PASSWORD = os.getenv("XUI_PASSWORD", "")

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
)

CF_API_TOKEN = os.getenv(
    "CLOUDFLARE_API_TOKEN",
    "",
)

CF_ZONE_ID = os.getenv(
    "CLOUDFLARE_ZONE_ID",
    "",
)


app = FastAPI(
    title=APP_NAME,
    version=VERSION,
)

serializer = URLSafeTimedSerializer(SESSION_SECRET)


def db():
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = db()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            uuid TEXT,
            protocol TEXT,
            inbound_id INTEGER,
            volume INTEGER DEFAULT 0,
            expiry INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            details TEXT,
            created_at INTEGER
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )

    connection.commit()
    connection.close()


init_db()


def log_action(action: str, details: str = ""):

    connection = db()

    connection.execute(
        """
        INSERT INTO logs(action, details, created_at)
        VALUES (?, ?, ?)
        """,
        (
            action,
            details,
            int(time.time()),
        ),
    )

    connection.commit()
    connection.close()


def create_session():
    return serializer.dumps(
        {
            "admin": True,
            "iat": int(time.time()),
        }
    )


def is_authenticated(request: Request):

    token = request.cookies.get("pompnet_session")

    if not token:
        return False

    try:
        data = serializer.loads(
            token,
            max_age=60 * 60 * 24,
        )

        return bool(data.get("admin"))

    except Exception:
        return False


def require_auth(request: Request):

    if not is_authenticated(request):
        raise HTTPException(
            status_code=401,
            detail="احراز هویت لازم است",
        )


def xui():

    if not XUI_URL:
        raise HTTPException(
            status_code=503,
            detail="XUI_URL تنظیم نشده است",
        )

    return SanaeiAdapter(
        XUI_URL,
        XUI_USERNAME,
        XUI_PASSWORD,
    )


@app.get("/", response_class=HTMLResponse)
async def home():

    file_path = "pompnet_ui2026.html"

    if not os.path.exists(file_path):
        return HTMLResponse(
            "<h1>PompNet UI file not found</h1>",
            status_code=500,
        )

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:

        return HTMLResponse(
            file.read()
        )


@app.get("/health")
async def health():

    return {
        "status": "ok",
        "app": APP_NAME,
        "version": VERSION,
        "timestamp": int(time.time()),
    }


@app.post("/login")
async def login(request: Request):

    body = await request.json()

    password = str(
        body.get("password", "")
    )

    if not secrets.compare_digest(
        password,
        ADMIN_PASSWORD,
    ):
        log_action(
            "login_failed",
            "wrong password",
        )

        raise HTTPException(
            status_code=401,
            detail="رمز عبور اشتباه است",
        )

    token = create_session()

    response = JSONResponse(
        {
            "success": True,
            "message": "خوش آمدید محمد",
        }
    )

    response.set_cookie(
        "pompnet_session",
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )

    log_action(
        "login",
        "admin login",
    )

    return response


@app.post("/logout")
async def logout():

    response = JSONResponse(
        {
            "success": True
        }
    )

    response.delete_cookie(
        "pompnet_session"
    )

    return response


@app.get("/api/system")
async def system_info(
    request: Request,
):

    require_auth(request)

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()

    return {
        "cpu": psutil.cpu_percent(
            interval=0.2
        ),
        "ram": {
            "percent": memory.percent,
            "total": memory.total,
            "used": memory.used,
            "available": memory.available,
        },
        "disk": {
            "percent": disk.percent,
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
        },
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
        },
        "load": (
            os.getloadavg()
            if hasattr(os, "getloadavg")
            else []
        ),
    }


@app.get("/api/overview")
async def overview(
    request: Request,
):

    require_auth(request)

    connection = db()

    users = connection.execute(
        "SELECT COUNT(*) FROM clients"
    ).fetchone()[0]

    enabled = connection.execute(
        "SELECT COUNT(*) FROM clients WHERE enabled=1"
    ).fetchone()[0]

    connection.close()

    return {
        "users": users,
        "enabled_users": enabled,
        "version": VERSION,
        "app": APP_NAME,
    }


@app.get("/api/clients")
async def clients(
    request: Request,
):

    require_auth(request)

    connection = db()

    rows = connection.execute(
        """
        SELECT *
        FROM clients
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


@app.post("/api/clients")
async def add_client(
    request: Request,
):

    require_auth(request)

    body = await request.json()

    name = str(
        body.get("name", "")
    ).strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="نام کاربر الزامی است",
        )

    client_uuid = body.get(
        "uuid"
    ) or SanaeiAdapter.new_uuid()

    connection = db()

    cursor = connection.execute(
        """
        INSERT INTO clients
        (
            name,
            email,
            uuid,
            protocol,
            inbound_id,
            volume,
            expiry,
            enabled,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            body.get("email"),
            client_uuid,
            body.get(
                "protocol",
                "vless",
            ),
            body.get(
                "inbound_id"
            ),
            int(
                body.get(
                    "volume",
                    0,
                )
            ),
            int(
                body.get(
                    "expiry",
                    0,
                )
            ),
            1,
            int(time.time()),
        ),
    )

    connection.commit()

    client_id = cursor.lastrowid

    connection.close()

    log_action(
        "client_created",
        f"id={client_id}",
    )

    return {
        "success": True,
        "id": client_id,
        "uuid": client_uuid,
    }


@app.delete("/api/clients/{client_id}")
async def delete_client(
    client_id: int,
    request: Request,
):

    require_auth(request)

    connection = db()

    row = connection.execute(
        "SELECT * FROM clients WHERE id=?",
        (client_id,),
    ).fetchone()

    if not row:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="کاربر پیدا نشد",
        )

    connection.execute(
        "DELETE FROM clients WHERE id=?",
        (client_id,),
    )

    connection.commit()
    connection.close()

    log_action(
        "client_deleted",
        f"id={client_id}",
    )

    return {
        "success": True
    }


@app.get("/api/logs")
async def logs(
    request: Request,
):

    require_auth(request)

    connection = db()

    rows = connection.execute(
        """
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 200
        """
    ).fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


@app.get("/api/xui/status")
async def xui_status(
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:
        result = await adapter.login()

        return {
            "connected": True,
            "result": result,
        }

    except Exception as exc:

        return JSONResponse(
            {
                "connected": False,
                "error": str(exc),
            },
            status_code=502,
        )

    finally:
        await adapter.close()


@app.get("/api/xui/inbounds")
async def xui_inbounds(
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:
        result = await adapter.inbounds()

        log_action(
            "xui_inbounds",
            "read",
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    finally:
        await adapter.close()


@app.get("/api/xui/inbound/{inbound_id}")
async def xui_inbound(
    inbound_id: int,
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:
        return await adapter.inbound(
            inbound_id
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    finally:
        await adapter.close()


@app.get("/api/xui/client-traffic/{email}")
async def xui_client_traffic(
    email: str,
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:
        return await adapter.client_traffic(
            email
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    finally:
        await adapter.close()


@app.post("/api/xui/reset/{email}")
async def xui_reset(
    email: str,
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:

        result = await adapter.reset_client_traffic(
            email
        )

        log_action(
            "xui_reset_traffic",
            email,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    finally:
        await adapter.close()


@app.post("/api/xui/restart")
async def xui_restart(
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:

        result = await adapter.restart_xray()

        log_action(
            "xray_restart",
            "real API request",
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    finally:
        await adapter.close()


@app.get("/api/xui/server")
async def xui_server(
    request: Request,
):

    require_auth(request)

    adapter = xui()

    try:

        return await adapter.server_status()

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    finally:
        await adapter.close()


@app.get("/sub/{token}")
async def subscription(
    token: str,
):

    connection = db()

    row = connection.execute(
        """
        SELECT *
        FROM clients
        WHERE uuid=?
        AND enabled=1
        """,
        (token,),
    ).fetchone()

    connection.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found",
        )

    result = {
        "name": row["name"],
        "uuid": row["uuid"],
        "protocol": row["protocol"],
        "volume": row["volume"],
        "expiry": row["expiry"],
    }

    encoded = base64.b64encode(
        json.dumps(
            result,
            ensure_ascii=False,
        ).encode()
    ).decode()

    return Response(
        content=encoded,
        media_type="text/plain",
    )


@app.get("/api/qr")
async def qr(
    request: Request,
    text: str,
):

    require_auth(request)

    image = qrcode.make(text)

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="image/png",
    )


@app.get("/api/export")
async def export_data(
    request: Request,
):

    require_auth(request)

    connection = db()

    clients = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM clients"
        ).fetchall()
    ]

    logs = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM logs"
        ).fetchall()
    ]

    connection.close()

    return {
        "version": VERSION,
        "exported_at": int(time.time()),
        "clients": clients,
        "logs": logs,
    }


@app.post("/api/import")
async def import_data(
    request: Request,
):

    require_auth(request)

    body = await request.json()

    clients = body.get(
        "clients",
        [],
    )

    connection = db()

    for client in clients:

        connection.execute(
            """
            INSERT INTO clients
            (
                name,
                email,
                uuid,
                protocol,
                inbound_id,
                volume,
                expiry,
                enabled,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client.get("name"),
                client.get("email"),
                client.get("uuid"),
                client.get("protocol"),
                client.get("inbound_id"),
                client.get("volume", 0),
                client.get("expiry", 0),
                client.get("enabled", 1),
                client.get(
                    "created_at",
                    int(time.time()),
                ),
            ),
        )

    connection.commit()
    connection.close()

    log_action(
        "import",
        f"{len(clients)} clients",
    )

    return {
        "success": True,
        "imported": len(clients),
    }


@app.post("/api/telegram/test")
async def telegram_test(
    request: Request,
):

    require_auth(request)

    token = (
        TELEGRAM_BOT_TOKEN
        or os.getenv(
            "TELEGRAM_BOT_TOKEN",
            "",
        )
    )

    if not token:

        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_BOT_TOKEN تنظیم نشده است",
        )

    url = (
        "https://api.telegram.org/"
        f"bot{token}/getMe"
    )

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        response = await client.get(url)

    if response.status_code >= 400:

        raise HTTPException(
            status_code=502,
            detail=response.text[:500],
        )

    data = response.json()

    log_action(
        "telegram_test",
        "getMe",
    )

    return data


@app.get("/api/cloudflare/status")
async def cloudflare_status(
    request: Request,
):

    require_auth(request)

    if not CF_API_TOKEN:

        return {
            "connected": False,
            "error": "CLOUDFLARE_API_TOKEN تنظیم نشده",
        }

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        response = await client.get(
            "https://api.cloudflare.com/client/v4/user/tokens/verify",
            headers={
                "Authorization":
                    f"Bearer {CF_API_TOKEN}",
                "Content-Type":
                    "application/json",
            },
        )

    try:
        data = response.json()
    except Exception:
        data = {
            "raw": response.text
        }

    return data


@app.get("/api/cloudflare/dns")
async def cloudflare_dns(
    request: Request,
):

    require_auth(request)

    if not CF_API_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Cloudflare API token تنظیم نشده است",
        )

    if not CF_ZONE_ID:
        raise HTTPException(
            status_code=503,
            detail="Cloudflare Zone ID تنظیم نشده است",
        )

    async with httpx.AsyncClient(
        timeout=20
    ) as client:

        response = await client.get(
            f"https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records",
            headers={
                "Authorization":
                    f"Bearer {CF_API_TOKEN}",
                "Content-Type":
                    "application/json",
            },
        )

    if response.status_code >= 400:

        raise HTTPException(
            status_code=502,
            detail=response.text[:500],
        )

    return response.json()
