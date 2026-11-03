"""Nepal address reference data and validation (ORD-012).

Structured addresses are required from Phase 2 because courier routing and COD intelligence key on
(origin district → destination district). Province and district lists follow the 2015 constitution
(7 provinces, 77 districts). Municipality is free text until a verified municipality list is loaded
(GAP-NP-MUNICIPALITIES): 753 local levels are too many to embed from memory without a source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PROVINCES: dict[str, tuple[str, str]] = {
    "koshi": ("Koshi", "कोशी"),
    "madhesh": ("Madhesh", "मधेश"),
    "bagmati": ("Bagmati", "बागमती"),
    "gandaki": ("Gandaki", "गण्डकी"),
    "lumbini": ("Lumbini", "लुम्बिनी"),
    "karnali": ("Karnali", "कर्णाली"),
    "sudurpashchim": ("Sudurpashchim", "सुदूरपश्चिम"),
}

_DISTRICTS_BY_PROVINCE: dict[str, tuple[str, ...]] = {
    "koshi": (
        "Bhojpur", "Dhankuta", "Ilam", "Jhapa", "Khotang", "Morang", "Okhaldhunga", "Panchthar",
        "Sankhuwasabha", "Solukhumbu", "Sunsari", "Taplejung", "Terhathum", "Udayapur",
    ),
    "madhesh": ("Bara", "Dhanusha", "Mahottari", "Parsa", "Rautahat", "Saptari", "Sarlahi", "Siraha"),
    "bagmati": (
        "Bhaktapur", "Chitwan", "Dhading", "Dolakha", "Kathmandu", "Kavrepalanchok", "Lalitpur",
        "Makwanpur", "Nuwakot", "Ramechhap", "Rasuwa", "Sindhuli", "Sindhupalchok",
    ),
    "gandaki": (
        "Baglung", "Gorkha", "Kaski", "Lamjung", "Manang", "Mustang", "Myagdi", "Nawalpur", "Parbat",
        "Syangja", "Tanahun",
    ),
    "lumbini": (
        "Arghakhanchi", "Banke", "Bardiya", "Dang", "Gulmi", "Kapilvastu", "Parasi", "Palpa", "Pyuthan",
        "Rolpa", "Rukum East", "Rupandehi",
    ),
    "karnali": (
        "Dailekh", "Dolpa", "Humla", "Jajarkot", "Jumla", "Kalikot", "Mugu", "Salyan", "Surkhet",
        "Rukum West",
    ),
    "sudurpashchim": (
        "Achham", "Baitadi", "Bajhang", "Bajura", "Dadeldhura", "Darchula", "Doti", "Kailali", "Kanchanpur",
    ),
}  # fmt: skip


def _code(name: str) -> str:
    return re.sub(r"[^a-z]+", "_", name.lower()).strip("_")


# district code → (English name, province code)
DISTRICTS: dict[str, tuple[str, str]] = {
    _code(d): (d, prov) for prov, names in _DISTRICTS_BY_PROVINCE.items() for d in names
}
assert len(DISTRICTS) == 77, "Nepal has 77 districts"

MAX_WARD = 35  # the largest municipalities have 32-33 wards
_MOBILE = re.compile(r"^(?:\+?977[-\s]?)?0?(9[678]\d{8})$")


def normalize_phone(raw: str | None) -> str | None:
    """Nepal mobile → +977XXXXXXXXXX; None if it isn't a Nepal mobile number."""
    if not raw:
        return None
    m = _MOBILE.match(re.sub(r"[\s\-().]", "", raw.strip()))
    return f"+977{m.group(1)}" if m else None


def find_phone(text: str) -> str | None:
    """First Nepal mobile number mentioned in free text (chat messages)."""
    for m in re.finditer(r"(?:\+?977[-\s]?)?9[678][\d\s-]{8,12}", text):
        n = normalize_phone(m.group(0))
        if n:
            return n
    return None


def district_code(value: str | None) -> str | None:
    """Accepts a code or an English name in any case ("kathmandu", "Rukum West")."""
    if not value:
        return None
    c = _code(value)
    return c if c in DISTRICTS else None


@dataclass
class AddressCheck:
    errors: dict[str, str]
    completeness: float  # 0..1, used later by COD/courier intelligence

    @property
    def ok(self) -> bool:
        return not self.errors


REQUIRED = ("recipient_name", "phone", "province", "district", "municipality", "ward")
OPTIONAL_SIGNAL = ("area", "landmark")


def check_address(a: dict[str, object]) -> AddressCheck:
    """Validates a structured Nepal address. District must belong to the province."""
    errors: dict[str, str] = {}
    for f in REQUIRED:
        if a.get(f) in (None, ""):
            errors[f] = "required"
    prov = a.get("province")
    if prov and prov not in PROVINCES:
        errors["province"] = "unknown_province"
    dist = a.get("district")
    if dist:
        if dist not in DISTRICTS:
            errors["district"] = "unknown_district"
        elif prov in PROVINCES and DISTRICTS[str(dist)][1] != prov:
            errors["district"] = "district_not_in_province"
    ward = a.get("ward")
    if ward not in (None, "") and not (isinstance(ward, int) and 1 <= ward <= MAX_WARD):
        errors["ward"] = "invalid_ward"
    phone = a.get("phone")
    if phone and normalize_phone(str(phone)) is None:
        errors["phone"] = "invalid_phone"
    filled = sum(1 for f in (*REQUIRED, *OPTIONAL_SIGNAL) if a.get(f) not in (None, "") and f not in errors)
    return AddressCheck(errors, round(filled / (len(REQUIRED) + len(OPTIONAL_SIGNAL)), 2))
