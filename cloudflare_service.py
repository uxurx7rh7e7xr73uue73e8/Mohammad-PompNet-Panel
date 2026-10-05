import httpx

from config import (
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_ZONE_ID
)


API = (
    "https://api.cloudflare.com/client/v4"
)


def headers():

    return {
        "Authorization":
            f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type":
            "application/json"
    }


async def connection_status():

    if not CLOUDFLARE_API_TOKEN:

        return {
            "configured": False,
            "connected": False
        }

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        if CLOUDFLARE_ZONE_ID:

            url = (
                f"{API}/zones/"
                f"{CLOUDFLARE_ZONE_ID}"
            )

        else:

            url = (
                f"{API}/zones"
            )

        response = await client.get(
            url,
            headers=headers()
        )

    data = response.json()

    return {
        "configured": True,
        "connected":
            bool(
                data.get("success")
            ),
        "result":
            data.get("result")
    }
