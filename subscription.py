import base64

from database import get_db


def get_client_by_token(token):

    db = get_db()

    row = db.execute(
        """
        SELECT *
        FROM clients
        WHERE token=?
        AND enabled=1
        """,
        (token,)
    ).fetchone()

    db.close()

    return row


def build_subscription(token):

    client = get_client_by_token(
        token
    )

    if not client:

        return None

    raw = client["link"].strip()

    encoded = base64.b64encode(
        raw.encode("utf-8")
    ).decode("ascii")

    return encoded


def build_raw_subscription(token):

    client = get_client_by_token(
        token
    )

    if not client:

        return None

    return client["link"].strip()
