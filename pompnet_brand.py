from pathlib import Path
import re

ROOT = Path("/app")

REPLACEMENTS = [
    ("https://t.me/ahbpanel", "https://t.me/pompnet"),
    ("https://t.me/ahb_panel", "https://t.me/pompnet"),

    ("@ahb_panel", "@NovaTunneli"),

    ("Created By Ahb", "Created By Mohammad Pomp Net"),
    ("Created by Ahb", "Created by Mohammad Pomp Net"),

    ("AHBPanel", "PompNet"),
    ("AHB PANEL", "POMP NET"),
    ("AHB Panel", "POMP NET"),
    ("Ahb Panel", "POMP NET"),

    ("ahbpanel", "pompnet"),
    ("ahb_panel", "pompnet"),
    ("ahb-panel", "pomp-net"),

    ("پنل AHB", "پنل POMP NET"),
    ("ای اچ بی پنل", "POMP NET"),
]

TEXT_EXTENSIONS = {
    ".py",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".json",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
}

SKIP = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

def is_text_file(path):
    return path.suffix.lower() in TEXT_EXTENSIONS

def replace_text(path):
    try:
        data = path.read_text(encoding="utf-8")
    except Exception:
        return

    original = data

    for old, new in REPLACEMENTS:
        data = data.replace(old, new)

    # Keep original authentication system,
    # but make the default Railway credentials admin/admin.
    data = data.replace(
        'os.environ.get("ADMIN_USERNAME", "").strip()',
        'os.environ.get("ADMIN_USERNAME", "admin").strip()'
    )

    data = data.replace(
        'os.environ.get("ADMIN_PASSWORD", "").strip()',
        'os.environ.get("ADMIN_PASSWORD", "admin").strip()'
    )

    if data != original:
        path.write_text(data, encoding="utf-8")

def main():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if any(part in SKIP for part in path.parts):
            continue

        if not is_text_file(path):
            continue

        replace_text(path)

    main_py = ROOT / "main.py"

    if main_py.exists():
        data = main_py.read_text(encoding="utf-8")

        # Force application branding.
        data = re.sub(
            r'APP_NAME\s*=\s*["\'][^"\']*["\']',
            'APP_NAME = "POMP NET"',
            data,
            count=1
        )

        data = re.sub(
            r'SUPPORT_USERNAME\s*=\s*["\'][^"\']*["\']',
            'SUPPORT_USERNAME = "@NovaTunneli"',
            data,
            count=1
        )

        data = re.sub(
            r'SUPPORT_URL\s*=\s*["\'][^"\']*["\']',
            'SUPPORT_URL = "https://t.me/NovaTunneli"',
            data,
            count=1
        )

        # Admin defaults.
        data = data.replace(
            'os.environ.get("ADMIN_USERNAME", "").strip()',
            'os.environ.get("ADMIN_USERNAME", "admin").strip()'
        )

        data = data.replace(
            'os.environ.get("ADMIN_PASSWORD", "").strip()',
            'os.environ.get("ADMIN_PASSWORD", "admin").strip()'
        )

        main_py.write_text(data, encoding="utf-8")

    print("====================================")
    print(" POMP NET BRANDING COMPLETE")
    print(" Username: admin")
    print(" Password: admin")
    print("====================================")

if __name__ == "__main__":
    main()
