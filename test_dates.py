import dateparser
from datetime import datetime

dates = ["aug 2025", "2 weeksleft", "1 weekleft", "1 yearleft", "10 months left"]
for d in dates:
    parsed = dateparser.parse(d, settings={'STRICT_PARSING': False})
    if parsed:
        print(f"'{d}' -> {parsed.replace(tzinfo=None)} (Expired: {parsed.replace(tzinfo=None) < datetime.now()})")
    else:
        print(f"'{d}' -> None")
