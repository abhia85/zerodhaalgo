# fix_imports.py
# Run from repo root. It rewrites local imports under backend/app to use the app package
# so that inside the container you can import e.g. app.kite_client, app.data_fetcher, etc.

import re
from pathlib import Path

ROOT = Path("zerodha/zerodha_trading_app_final4/backend/app")
if not ROOT.exists():
    print("ERROR: expected backend app dir not found at:", ROOT)
    raise SystemExit(1)

# local module names we expect to appear as bare imports
mods = [
    "kite_client",
    "backtester",
    "models_db",
    "kite_auth_exchange",
    "data_fetcher",
    "workers_stream",
    "workers_streams",
    "workers"
]
mods_regex = "(" + "|".join(re.escape(m) for m in mods) + ")"

modified_files = []

for p in sorted(ROOT.rglob("*.py")):
    text = p.read_text(encoding="utf8")
    orig = text

    lines = []
    for line in text.splitlines(keepends=True):
        # skip lines that already import from app or import app.
        if re.match(r'^\s*from\s+app\.', line) or re.match(r'^\s*import\s+app\.', line):
            lines.append(line)
            continue

        m_from = re.match(r'^(\s*)from\s+' + mods_regex + r'\s+import\s+(.*)', line)
        if m_from:
            indent = m_from.group(1) or ""
            mod = m_from.group(2)
            rest = m_from.group(3)
            lines.append(f"{indent}from app.{mod} import {rest}\n")
            continue

        m_imp = re.match(r'^(\s*)import\s+' + mods_regex + r'(\s*(#.*)?)?$', line)
        if m_imp:
            indent = m_imp.group(1) or ""
            mod = m_imp.group(2)
            comment = m_imp.group(3) or ""
            # convert 'import kite_client' -> 'from app import kite_client'
            lines.append(f"{indent}from app import {mod}{comment}\n")
            continue

        # otherwise keep the line
        lines.append(line)

    new_text = "".join(lines)
    if new_text != orig:
        p.write_text(new_text, encoding="utf8")
        modified_files.append(str(p))

print("Modified files:", modified_files)
if not modified_files:
    print("No bare local imports found/changed.")
