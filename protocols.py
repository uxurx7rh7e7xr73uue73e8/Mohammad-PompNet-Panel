from urllib.parse import urlparse


SUPPORTED_PROTOCOLS = {

    "vless": "VLESS",

    "vmess": "VMESS",

    "trojan": "Trojan",

    "ss": "Shadowsocks",

    "hysteria2": "Hysteria2",

    "hy2": "Hysteria2",

    "tuic": "TUIC"

}


def detect_protocol(link: str):

    if not link:

        return None

    value = link.strip().lower()

    for scheme, name in SUPPORTED_PROTOCOLS.items():

        if value.startswith(
            scheme + "://"
        ):

            return name

    return None


def validate_link(link: str):

    protocol = detect_protocol(link)

    if not protocol:

        return {
            "valid": False,
            "protocol": None,
            "error":
                "پروتکل پشتیبانی نمی‌شود."
        }

    parsed = urlparse(link)

    if not parsed.scheme:

        return {
            "valid": False,
            "protocol": protocol,
            "error":
                "لینک معتبر نیست."
        }

    return {
        "valid": True,
        "protocol": protocol
    }


def supported_protocols():

    return [
        "VLESS",
        "VMESS",
        "Trojan",
        "Shadowsocks",
        "Hysteria2",
        "TUIC"
    ]
