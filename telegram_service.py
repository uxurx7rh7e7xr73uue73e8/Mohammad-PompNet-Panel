import httpx


TELEGRAM_API = (
    "https://api.telegram.org/bot"
)


async def get_bot_info(token):

    url = (
        TELEGRAM_API
        + token
        + "/getMe"
    )

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        response = await client.get(
            url
        )

    if response.status_code != 200:

        return {
            "ok": False,
            "error":
                "Telegram API error"
        }

    data = response.json()

    if not data.get("ok"):

        return {
            "ok": False,
            "error":
                "Bot Token نامعتبر است."
        }

    result = data["result"]

    return {
        "ok": True,
        "id":
            result.get("id"),
        "username":
            result.get("username"),
        "first_name":
            result.get("first_name"),
        "can_join_groups":
            result.get(
                "can_join_groups"
            ),
        "can_read_all_group_messages":
            result.get(
                "can_read_all_group_messages"
            )
    }


async def send_message(
    token,
    chat_id,
    text
):

    url = (
        TELEGRAM_API
        + token
        + "/sendMessage"
    )

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    async with httpx.AsyncClient(
        timeout=15
    ) as client:

        response = await client.post(
            url,
            json=payload
        )

    return response.json()
