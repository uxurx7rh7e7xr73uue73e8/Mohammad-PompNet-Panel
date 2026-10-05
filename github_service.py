import httpx

from config import (
    GITHUB_TOKEN,
    GITHUB_REPOSITORY
)


async def repository_status():

    if not GITHUB_TOKEN:

        return {
            "configured": False,
            "repository":
                GITHUB_REPOSITORY
        }

    headers = {
        "Authorization":
            f"Bearer {GITHUB_TOKEN}",
        "Accept":
            "application/vnd.github+json"
    }

    url = (
        "https://api.github.com/repos/"
        + GITHUB_REPOSITORY
    )

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
        "connected":
            response.is_success,
        "repository":
            GITHUB_REPOSITORY,
        "private":
            data.get("private"),
        "default_branch":
            data.get(
                "default_branch"
            ),
        "html_url":
            data.get("html_url")
    }
