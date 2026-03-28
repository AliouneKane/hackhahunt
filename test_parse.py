import dateparser
from datetime import datetime
dates = [
    "Feb 11 - Mar 30, 2026",
    "2026-03-29",
    "byOFAaoût 21, 2023",
    "Mar 21 - 28, 2026",
    None,
    "TBD",
    "2023-01-01"
]
now = datetime.now()
for d in dates:
    if not d: continue
    parsed = dateparser.parse(d, settings={'STRICT_PARSING': False})
    if parsed:
        parsed = parsed.replace(tzinfo=None)
        expired = parsed < now
        print(f"'{d}' -> {parsed} (Expired: {expired})")
    else:
        print(f"'{d}' -> Could not parse")
