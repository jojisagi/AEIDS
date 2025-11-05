# view/validators.py
import re

EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
HOUSE_RE = re.compile(r"^(?:\d{1,6}(?:[A-Z])?(?:-\d{1,4})?|s/?n)$", re.I)
PHONE_10_RE = re.compile(r"^\d{10}$")
PHONE_PLUS52_RE = re.compile(r"^\+52\d{10}$")

def normalize_mx_phone_strict(raw: str) -> str | None:
    s = (raw or "").strip()
    if PHONE_10_RE.fullmatch(s): return s
    if PHONE_PLUS52_RE.fullmatch(s): return s[-10:]
    return None

def normalize_house(s: str) -> str:
    s = (s or "").strip().upper().replace(" ", "")
    s = s.replace("SINNUMERO", "S/N").replace("S/N.", "S/N")
    if s in ("SN", "S-N"): s = "S/N"
    return s