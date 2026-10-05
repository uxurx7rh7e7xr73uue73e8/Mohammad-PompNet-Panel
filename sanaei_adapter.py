import json
import uuid
from typing import Any, Optional

import httpx


class SanaeiAdapter:
    """
    Adapter ارتباطی با Sanaei / 3x-ui.

    نکته:
    هیچ داده ساختگی تولید نمی‌کند.
    اگر API پاسخ معتبر ندهد، خطا را به PompNet برمی‌گرداند.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 20.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username or ""
        self.password = password or ""
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False,
        )
        self.logged_in = False

    async def close(self):
        await self.client.aclose()

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def login(self) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("XUI_URL تنظیم نشده است")

        if not self.username or not self.password:
            raise RuntimeError("XUI_USERNAME یا XUI_PASSWORD تنظیم نشده است")

        response = await self.client.post(
            self._url("/login"),
            data={
                "username": self.username,
                "password": self.password,
            },
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Sanaei login failed: HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except Exception:
            data = {}

        if isinstance(data, dict) and data.get("success") is False:
            raise RuntimeError(
                data.get("msg")
                or data.get("message")
                or "Sanaei login failed"
            )

        self.logged_in = True

        return {
            "success": True,
            "status_code": response.status_code,
            "message": "اتصال به Sanaei برقرار شد",
            "data": data,
        }

    async def ensure_login(self):
        if not self.logged_in:
            await self.login()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> Any:

        await self.ensure_login()

        response = await self.client.request(
            method,
            self._url(path),
            params=params,
            json=json_data,
            data=data,
        )

        if response.status_code in (401, 403):
            self.logged_in = False
            await self.login()

            response = await self.client.request(
                method,
                self._url(path),
                params=params,
                json=json_data,
                data=data,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"Sanaei API HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            return response.json()

        try:
            return response.json()
        except Exception:
            return {
                "success": True,
                "raw": response.text,
            }

    async def status(self):
        return await self.request(
            "GET",
            "/panel/api/inbounds/list",
        )

    async def inbounds(self):
        return await self.request(
            "GET",
            "/panel/api/inbounds/list",
        )

    async def inbound(self, inbound_id: int):
        return await self.request(
            "GET",
            f"/panel/api/inbounds/get/{inbound_id}",
        )

    async def add_inbound(self, payload: dict):
        return await self.request(
            "POST",
            "/panel/api/inbounds/add",
            json_data=payload,
        )

    async def update_inbound(
        self,
        inbound_id: int,
        payload: dict,
    ):
        return await self.request(
            "POST",
            f"/panel/api/inbounds/update/{inbound_id}",
            json_data=payload,
        )

    async def delete_inbound(self, inbound_id: int):
        return await self.request(
            "POST",
            f"/panel/api/inbounds/del/{inbound_id}",
        )

    async def client_traffic(
        self,
        email: str,
    ):
        return await self.request(
            "GET",
            f"/panel/api/inbounds/getClientTraffics/{email}",
        )

    async def reset_client_traffic(
        self,
        email: str,
    ):
        return await self.request(
            "POST",
            f"/panel/api/inbounds/resetClientTraffic/{email}",
        )

    async def delete_client(
        self,
        inbound_id: int,
        client_id: str,
    ):
        return await self.request(
            "POST",
            f"/panel/api/inbounds/{inbound_id}/delClient/{client_id}",
        )

    async def create_client(
        self,
        inbound_id: int,
        client: dict,
    ):
        """
        client باید مطابق ساختار API نسخه نصب‌شده باشد.
        """

        settings = {
            "clients": [client]
        }

        payload = {
            "id": inbound_id,
            "settings": json.dumps(settings),
        }

        return await self.request(
            "POST",
            f"/panel/api/inbounds/addClient",
            json_data=payload,
        )

    async def update_client(
        self,
        inbound_id: int,
        client: dict,
    ):
        settings = {
            "clients": [client]
        }

        payload = {
            "id": inbound_id,
            "settings": json.dumps(settings),
        }

        return await self.request(
            "POST",
            f"/panel/api/inbounds/updateClient/{inbound_id}",
            json_data=payload,
        )

    @staticmethod
    def new_uuid() -> str:
        return str(uuid.uuid4())

    async def restart_xray(self):
        return await self.request(
            "POST",
            "/panel/api/server/restartXray",
        )

    async def server_status(self):
        return await self.request(
            "GET",
            "/panel/api/server/status",
        )
